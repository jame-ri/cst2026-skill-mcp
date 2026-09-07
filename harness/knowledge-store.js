import fs from "node:fs";
import path from "node:path";
import { createHash, randomUUID } from "node:crypto";

const hash = (value) => createHash("sha256").update(value).digest("hex");
const canonical = (value) => JSON.stringify(value, (_, item) =>
  item && typeof item === "object" && !Array.isArray(item)
    ? Object.fromEntries(Object.keys(item).sort().map((key) => [key, item[key]])) : item);

import { containedPath, relativePath } from "../shared/paths.js";
export { containedPath, relativePath } from "../shared/paths.js";


function text(value, field, max = 2000) {
  if (typeof value !== "string" || !value.trim() || value.length > max) throw new Error("Invalid " + field + ".");
  if (/[a-z]:[\\/]|\\\\|(?:^|\s)\/(?:[^\s/]+\/|[A-Za-z])/i.test(value)) {
    throw new Error(field + " contains an absolute path; use a relative reference or a parameter.");
  }
  return value.trim();
}

function strings(value, field, required = false) {
  if (value === undefined && !required) return [];
  if (!Array.isArray(value) || value.length > 32 || (required && !value.length)) throw new Error("Invalid " + field + ".");
  return value.map((item) => text(item, field));
}

function object(value, field) {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Invalid " + field + ".");
  return value;
}

function readJson(file) {
  if (fs.statSync(file).size > 4 * 1024 * 1024) throw new Error("Knowledge or source record exceeds 4 MiB.");
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

// Immutable publications avoid partial reads, lost observations, and duplicate
// success counts when several agent processes share the same knowledge store.
function publish(file, value) {
  const temporary = file + "." + randomUUID() + ".tmp";
  let fd;
  try {
    fd = fs.openSync(temporary, "wx", 0o600);
    fs.writeFileSync(fd, canonical(value) + "\n", "utf8");
    fs.fsyncSync(fd);
    fs.closeSync(fd);
    fd = undefined;
    try {
      fs.linkSync(temporary, file);
      return true;
    } catch (error) {
      if (error.code !== "EEXIST") throw error;
      if (canonical(readJson(file)) !== canonical(value)) throw new Error("Conflicting immutable knowledge record.");
      return false;
    }
  } finally {
    if (fd !== undefined) fs.closeSync(fd);
    if (fs.existsSync(temporary)) fs.unlinkSync(temporary);
  }
}

export class KnowledgeStore {
  constructor(repoRoot, env = process.env) {
    this.repoRoot = fs.realpathSync(repoRoot);
    this.directory = relativePath(env.CST_KNOWLEDGE_DIR || "design-records/knowledge");
    this.enabled = env.CST_KNOWLEDGE_ENABLED !== "0";
    this.autoCapture = env.CST_KNOWLEDGE_AUTO_CAPTURE !== "0";
    this.stableRuns = Number(env.CST_KNOWLEDGE_STABLE_RUNS || 2);
    if (!Number.isInteger(this.stableRuns) || this.stableRuns < 2 || this.stableRuns > 100) {
      throw new Error("CST_KNOWLEDGE_STABLE_RUNS must be an integer between 2 and 100.");
    }
    containedPath(this.repoRoot, this.directory);
  }

  file(relative) {
    return containedPath(this.repoRoot, this.directory + "/" + relative);
  }

  definition(operation) {
    const specified = operation.knowledge;
    const repair = operation.repair_action;
    const rawSteps = specified?.steps ?? operation.steps ?? (repair ? (Array.isArray(repair) ? repair : [repair]) : undefined);
    if (specified === undefined && rawSteps === undefined) return null;
    const raw = specified === undefined ? operation : object(specified, "knowledge");
    const kind = raw.kind ?? (operation.error_signature || raw.signature ? "lesson" : "workflow");
    if (!["workflow", "lesson"].includes(kind)) throw new Error("knowledge.kind must be workflow or lesson.");
    const applicability = object(raw.applicability ?? {}, "applicability");
    if (Object.keys(applicability).length > 16) throw new Error("Too many applicability fields.");
    return {
      schema_version: 1,
      kind,
      title: text(raw.title ?? operation.title ?? operation.error_signature, "title", 240),
      category: text(raw.category ?? operation.category ?? operation.error_class ?? "general", "category", 80),
      signature: kind === "lesson" ? text(raw.signature ?? operation.error_signature, "signature", 1000) : null,
      diagnosis: raw.diagnosis || operation.diagnosis ? text(raw.diagnosis ?? operation.diagnosis, "diagnosis") : null,
      steps: strings(rawSteps, "steps", true),
      preconditions: strings(raw.preconditions, "preconditions"),
      parameters: strings(raw.parameters, "parameters"),
      applicability: Object.fromEntries(Object.entries(applicability).map(([key, value]) =>
        [text(key, "applicability key", 80), text(value, "applicability value", 240)]))
    };
  }

  evidence(verification) {
    if (verification === undefined) return null;
    object(verification, "verification");
    if (!["pass", "fail", "not_executed"].includes(verification.status)) throw new Error("Invalid verification status.");
    const summary = text(verification.summary, "verification.summary");
    const references = verification.evidence ?? [];
    if (!Array.isArray(references) || references.length > 8) throw new Error("Invalid verification evidence.");
    if (verification.status === "pass" && !references.length) throw new Error("A passing verification requires artifact evidence.");
    const evidence = references.map((reference) => {
      object(reference, "evidence reference");
      const relative = relativePath(reference.path);
      const file = containedPath(this.repoRoot, relative);
      const stat = fs.statSync(file);
      if (!stat.isFile() || stat.size > 16 * 1024 * 1024) throw new Error("Evidence must be a regular file no larger than 16 MiB.");
      const digest = hash(fs.readFileSync(file));
      if (reference.sha256 !== undefined && reference.sha256 !== digest) throw new Error("Evidence digest mismatch.");
      return { path: relative, sha256: digest, bytes: stat.size };
    });
    return { status: verification.status, summary, evidence, attestation: "agent_reported_with_artifact_digest" };
  }

  capture(args) {
    if (!this.enabled) return { status: "disabled" };
    const sourcePath = relativePath(args.manifest_path);
    const collection = args.collection ?? "operations";
    if (!["operations", "checkpoints"].includes(collection)) throw new Error("Invalid source collection.");
    const manifest = readJson(containedPath(this.repoRoot, sourcePath));
    const items = manifest[collection];
    const index = args.index ?? (Array.isArray(items) ? items.length - 1 : -1);
    if (!Number.isInteger(index) || index < 0 || !Array.isArray(items) || index >= items.length) throw new Error("Source operation not found.");
    const record = object(items[index], "source record");
    const operation = collection === "checkpoints" ? object(record.operation ?? {}, "operation") : record;
    const definition = this.definition(operation);
    if (!definition) return { status: "skipped", reason: "No reusable steps or repair action in this operation." };
    const verification = this.evidence(operation.verification);
    const executed = operation.executed === true && operation.execute !== false;
    const done = (collection === "checkpoints" ? record.status : operation.status) === "done";
    const outcome = verification?.status === "fail" || record.status === "failed" || operation.status === "failed"
      ? "failed" : executed && done && verification?.status === "pass" ? "verified" : "candidate";
    const source = { manifest_path: sourcePath, collection, index };
    const id = hash(canonical(definition));
    const observationId = hash(canonical(source));
    const relative = id + "/observations";
    fs.mkdirSync(this.file(relative), { recursive: true });
    publish(this.file(id + "/entry.json"), definition);
    const observation = {
      source,
      recorded_at: record.recorded_at ?? manifest.updated_at ?? manifest.created_at ?? null,
      outcome,
      executed,
      verification
    };
    const created = publish(this.file(relative + "/" + observationId + ".json"), observation);
    const entry = this.get(id);
    return { status: "stored", id, entry_status: entry.status, created,
      source, knowledge_path: this.directory + "/" + id + "/entry.json" };
  }

  captureAutomatically(args) {
    if (!this.enabled || !this.autoCapture) return { status: "disabled" };
    try {
      return this.capture(args);
    } catch (error) {
      // The design record already exists. A memory failure must not suggest
      // repeating an already successful CST mutation.
      return { status: "error", reason: error.code || "invalid_or_unwritable_knowledge",
        message: "Design record saved, but knowledge capture failed. Check relative paths, structured steps, evidence, and storage permissions; retry knowledge.capture_operation." };
    }
  }

  get(id) {
    if (!/^[a-f0-9]{64}$/.test(id)) throw new Error("Invalid knowledge entry ID.");
    if (!this.enabled) return { id, found: false, status: "disabled" };
    const definitionPath = this.file(id + "/entry.json");
    if (!fs.existsSync(definitionPath)) return { id, found: false };
    const definition = readJson(definitionPath);
    const observations = fs.readdirSync(this.file(id + "/observations"))
      .filter((name) => /^[a-f0-9]{64}\.json$/.test(name))
      .map((name) => readJson(this.file(id + "/observations/" + name)));
    const successes = new Set(observations.filter((item) => item.outcome === "verified").map((item) => item.source.manifest_path));
    const failures = observations.filter((item) => item.outcome === "failed").length;
    const status = failures ? "disputed" : successes.size >= this.stableRuns ? "stable" : successes.size ? "verified" : "candidate";
    return { id, found: true, ...definition, status, independent_successes: successes.size,
      observations, source_path: this.directory + "/" + id + "/entry.json",
      reuse_policy: "Check applicability and current project state; never execute stored steps automatically." };
  }

  sections({ kind, includeCandidates = false } = {}) {
    if (!this.enabled) return [];
    const root = containedPath(this.repoRoot, this.directory);
    if (!fs.existsSync(root)) return [];
    return fs.readdirSync(root).filter((id) => /^[a-f0-9]{64}$/.test(id)).map((id) => this.get(id))
      .filter((entry) => entry.found && (!kind || entry.kind === kind) &&
        (includeCandidates || ["verified", "stable"].includes(entry.status)))
      .map((entry) => ({
        source: entry.source_path, heading: entry.title, id: entry.id,
        status: entry.status, category: entry.category, kind: entry.kind,
        text: JSON.stringify({ ...entry, observations: entry.observations.slice(-3) }, null, 2)
      }));
  }
}

export const knowledgeTools = [
  {
    name: "knowledge.capture_operation",
    description: "Persist reusable steps or an error repair from an existing operation/checkpoint. Normally automatic; use for historical records or retrying failed capture. Does not run CST.",
    inputSchema: { type: "object", additionalProperties: false, properties: {
      manifest_path: { type: "string", description: "Repository-relative source manifest path." },
      collection: { type: "string", enum: ["operations", "checkpoints"], default: "operations" },
      index: { type: "integer", minimum: 0, description: "Zero-based source index; defaults to the latest record." }
    }, required: ["manifest_path"] }
  },
  {
    name: "knowledge.get_entry",
    description: "Read a learned workflow/lesson with applicability, evidence hashes, and provenance. Stored steps are data, not execution authorization.",
    inputSchema: { type: "object", additionalProperties: false, properties: {
      id: { type: "string", pattern: "^[a-f0-9]{64}$" }
    }, required: ["id"] }
  },
  {
    name: "knowledge.search_workflows",
    description: "Search automatically learned workflows. Default results include only verified/stable entries; never replays steps.",
    inputSchema: { type: "object", additionalProperties: false, properties: {
      query: { type: "string" },
      include_candidates: { type: "boolean", default: false },
      limit: { type: "integer", minimum: 1, maximum: 50, default: 10 },
      max_chars: { type: "integer", minimum: 200, maximum: 20000, default: 4000 }
    }, required: ["query"] }
  }
];
