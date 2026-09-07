import fs from "node:fs";
import path from "node:path";
import { containedPath, relativePath } from "../shared/paths.js";
import { digest, readJson, writeOnce } from "../shared/data.js";
import { InputError, atomicJson, withRecordLock } from "../shared/runtime.js";
import { candidateMetadata } from "./schema.js";

export class ApiStore {
  constructor(root) {
    this.root = root;
    this.relative = relativePath(process.env.CST_API_LIBRARY_DIR || "design-records/api-library");
    containedPath(root, this.relative);
  }
  path(suffix) { return containedPath(this.root, this.relative + "/" + suffix); }
  apiId(candidate) { return candidate.definition.id + "@" + candidate.definition.version; }
  registrationPath(apiId) { return this.path("registrations/" + digest(apiId) + ".json"); }

  async stage(candidatePath) {
    const definitionFile = containedPath(this.root, candidatePath);
    const definition = candidateMetadata(readJson(definitionFile, 64 * 1024));
    const implementation = containedPath(this.root, definition.implementation);
    if (!fs.statSync(implementation).isFile() || fs.statSync(implementation).size > 256 * 1024) throw new InputError("Python implementation must be a file of at most 256 KiB.");
    const source = fs.readFileSync(implementation);
    if (source.includes(0)) throw new InputError("Python source contains NUL bytes.");
    new TextDecoder("utf-8", { fatal: true }).decode(source);
    let referenceBytes = 0;
    const sourceReferences = definition.references.map(reference => {
      const filename = containedPath(this.root, reference);
      const stat = fs.statSync(filename);
      referenceBytes += stat.size;
      if (!stat.isFile() || stat.size > 16 * 1024 * 1024 || referenceBytes > 64 * 1024 * 1024) throw new InputError("References must be bounded source files.");
      return { path: reference, sha256: digest(fs.readFileSync(filename)) };
    });
    const content = { definition, implementation_sha256: digest(source), source_references: sourceReferences };
    const candidateId = digest(content);
    const directory = "candidates/" + candidateId;
    const relativeSource = this.relative + "/" + directory + "/implementation.py";
    const candidate = { schema_version: "cstapi.candidate.v1", candidate_id: candidateId,
      ...content, source_path: relativeSource };
    const file = this.path(directory + "/manifest.json");
    fs.mkdirSync(path.dirname(file), { recursive: true });
    await withRecordLock(file, async () => {
      writeOnce(this.path(directory + "/implementation.py"), source);
      writeOnce(file, candidate);
    });
    return { ok: true, execute: true, status: "candidate", candidate_id: candidateId,
      api_id: this.apiId(candidate), manifest_path: this.relative + "/" + directory + "/manifest.json",
      callable: false, note: "Source was snapshotted, not executed or validated against CST." };
  }

  candidate(candidateId) {
    if (!/^[a-f0-9]{64}$/.test(candidateId)) throw new InputError("candidate_id must be a SHA-256 identifier.");
    const item = readJson(this.path("candidates/" + candidateId + "/manifest.json"), 128 * 1024);
    const content = { definition: candidateMetadata(item.definition),
      implementation_sha256: item.implementation_sha256, source_references: item.source_references };
    const expectedSource = this.relative + "/candidates/" + candidateId + "/implementation.py";
    if (item.schema_version !== "cstapi.candidate.v1" || item.candidate_id !== candidateId ||
        digest(content) !== candidateId || item.source_path !== expectedSource) throw new InputError("Candidate metadata integrity check failed.");
    const source = containedPath(this.root, expectedSource);
    if (fs.statSync(source).size > 256 * 1024 || digest(fs.readFileSync(source)) !== item.implementation_sha256) throw new InputError("Candidate source integrity check failed.");
    return item;
  }

  registration(apiId) {
    const file = this.registrationPath(apiId);
    if (!fs.existsSync(file)) return null;
    const registration = readJson(file);
    if (registration.api_id !== apiId) throw new InputError("Registration identity mismatch.");
    const candidate = this.candidate(registration.candidate_id);
    if (this.apiId(candidate) !== apiId) throw new InputError("Registration and candidate identities differ.");
    const receipt = readJson(containedPath(this.root, registration.receipt_path), 16 * 1024 * 1024);
    if (digest(receipt) !== registration.receipt_sha256) throw new InputError("Stored verification receipt changed.");
    const stateFile = this.path("lifecycle/" + digest(apiId) + ".json");
    const state = fs.existsSync(stateFile) ? readJson(stateFile) : null;
    if (state && (state.api_id !== apiId || !["disputed", "retired"].includes(state.status))) throw new InputError("Invalid API lifecycle state.");
    return { ...registration, candidate, status: state?.status ?? "locally_verified", lifecycle: state };
  }

  list() {
    const directory = this.path("registrations");
    if (!fs.existsSync(directory)) return [];
    const files = fs.readdirSync(directory).filter(name => /^[a-f0-9]{64}\.json$/.test(name));
    if (files.length > 4096) throw new InputError("Local API catalog exceeds 4096 registrations.");
    return files.map(name => {
      const registration = readJson(this.path("registrations/" + name));
      if (digest(registration.api_id) + ".json" !== name) throw new InputError("Invalid registration filename.");
      return this.registration(registration.api_id);
    });
  }

  preflightPromotion(candidate) {
    const existing = this.registration(this.apiId(candidate));
    if (existing && (existing.candidate_id !== candidate.candidate_id || existing.status !== "locally_verified")) {
      throw new InputError("This API version is occupied, disputed or retired. Review the implementation and stage a new version.");
    }
  }

  async promote(candidate, result) {
    if (result.ok !== true || result.verification?.passed !== true || result.record?.status !== "stored") throw new InputError("Promotion requires a passing execution and a durable server receipt.");
    const receiptPath = relativePath(result.record.path);
    if (!receiptPath.startsWith("design-records/direct-operations/")) throw new InputError("Invalid execution receipt location.");
    const receipt = readJson(containedPath(this.root, receiptPath), 16 * 1024 * 1024);
    const outcome = receipt.result;
    if (receipt.tool !== "api.extension" || receipt.arguments?.candidate_id !== candidate.candidate_id ||
        receipt.arguments?.implementation_sha256 !== candidate.implementation_sha256 ||
        outcome?.ok !== true || outcome.candidate_id !== candidate.candidate_id ||
        outcome.implementation_sha256 !== candidate.implementation_sha256 ||
        outcome.verification?.passed !== true || outcome.execute !== true) throw new InputError("Receipt does not prove execution of this exact candidate.");
    const apiId = this.apiId(candidate);
    const file = this.registrationPath(apiId);
    fs.mkdirSync(path.dirname(file), { recursive: true });
    return withRecordLock(file, async () => {
      this.preflightPromotion(candidate);
      const existing = this.registration(apiId);
      if (existing) return { status: existing.status, api_id: apiId, already_registered: true };
      writeOnce(file, { schema_version: "cstapi.registration.v1", api_id: apiId,
        candidate_id: candidate.candidate_id, registered_at: new Date().toISOString(),
        receipt_path: receiptPath, receipt_sha256: digest(receipt),
        actual_cst_version: outcome.actual_cst_version });
      return { status: "locally_verified", api_id: apiId, callable: true,
        note: "Verified locally for the recorded invocation and CST year; not universally validated." };
    });
  }

  async setState(apiId, status, reason, operationId = null) {
    const file = this.registrationPath(apiId);
    if (!fs.existsSync(file)) throw new InputError("Only registered local extensions have a lifecycle.");
    return withRecordLock(file, async () => {
      const existing = this.registration(apiId);
      if (existing.status === "retired") return { status: "retired", api_id: apiId, already_retired: true };
      const stateFile = this.path("lifecycle/" + digest(apiId) + ".json");
      fs.mkdirSync(path.dirname(stateFile), { recursive: true });
      const previous = existing.lifecycle?.events ?? [];
      if (previous.length >= 1000) throw new InputError("Lifecycle history is full; archive it before adding events.");
      const event = { status, reason, operation_id: operationId, observed_at: new Date().toISOString() };
      atomicJson(stateFile, { api_id: apiId, status, events: [...previous, event] });
      return { api_id: apiId, status, callable: false };
    });
  }
}
