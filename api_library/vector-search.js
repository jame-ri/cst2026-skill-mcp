import fs from "node:fs";
import path from "node:path";
import { randomUUID } from "node:crypto";
import { containedPath, relativePath } from "../shared/paths.js";
import { digest, readJson } from "../shared/data.js";
import { InputError, atomicJson, runHelper, withRecordLock } from "../shared/runtime.js";

const brief = (item, score) => ({ api_id: item.api_id, description: item.description,
  status: item.status, effect: item.effect, cst_version: item.cst_version, score });
const document = item => [item.api_id, item.description, (item.tags ?? []).join(" "),
  JSON.stringify(item.input_schema)].join("\n").slice(0, 8000);
function normalize(values) {
  if (!Array.isArray(values) || !values.length || values.length > 8192 || values.some(value => !Number.isFinite(value))) throw new InputError("Embedding backend returned an invalid vector.");
  const norm = Math.hypot(...values);
  if (!Number.isFinite(norm) || norm === 0) throw new InputError("Embedding backend returned a zero or invalid norm.");
  return values.map(value => value / norm);
}

export class ApiVectorSearch {
  constructor(root, store) { this.root = root; this.store = store; }
  configuration() {
    const model = relativePath(process.env.CST_EMBEDDING_MODEL || "");
    const revision = process.env.CST_EMBEDDING_MODEL_ID;
    if (!revision || revision.length > 128) throw new InputError("Set CST_EMBEDDING_MODEL_ID to an explicit local model revision.");
    const directory = containedPath(this.root, model);
    if (!fs.statSync(directory).isDirectory()) throw new InputError("CST_EMBEDDING_MODEL must be an existing repository-relative model directory.");
    return { model, revision, identity: digest({ model, revision }) };
  }
  async embed(texts, config) {
    if (!texts.length || texts.length > 256) throw new InputError("A local vector batch supports 1-256 API descriptions.");
    const relative = this.store.relative + "/vector-runtime/" + randomUUID() + ".json";
    const request = containedPath(this.root, relative);
    fs.mkdirSync(path.dirname(request), { recursive: true });
    atomicJson(request, { model_path: config.model, texts });
    try {
      const executable = process.env.CST_EMBEDDING_PYTHON || (process.platform === "win32" ? "python.exe" : "python3");
      const execution = await runHelper([executable, "-B", "-m", "harness.embeddings", relative], {
        cwd: this.root, timeoutMs: 180000, maxOutputBytes: 8 * 1024 * 1024 });
      const result = execution.helper_result;
      if (execution.ok !== true || result?.ok !== true) throw new InputError(
        "Local embeddings are unavailable. Install the optional dependency and provide a complete local model explicitly; no automatic download is attempted.");
      if (!Array.isArray(result.vectors) || result.vectors.length !== texts.length) throw new InputError("Embedding count mismatch.");
      const vectors = result.vectors.map(normalize);
      if (vectors.some(vector => vector.length !== vectors[0].length)) throw new InputError("Embedding dimension mismatch.");
      return vectors;
    } finally {
      try { fs.unlinkSync(request); } catch (error) { if (error.code !== "ENOENT") throw error; }
    }
  }
  async reindex(entries) {
    const config = this.configuration();
    const vectors = await this.embed(entries.map(document), config);
    const file = this.store.path("vectors/index.json");
    fs.mkdirSync(path.dirname(file), { recursive: true });
    await withRecordLock(file, async () => atomicJson(file, {
      schema_version: "cstapi.vector-index.v1", model_identity: config.identity,
      catalog_fingerprint: digest(entries), built_at: new Date().toISOString(),
      entries: entries.map((entry, index) => ({ api_id: entry.api_id, vector: vectors[index] }))
    }));
    return { ok: true, execute: true, status: "indexed", api_count: entries.length,
      model: config.model, model_revision: config.revision,
      note: "Only API descriptions and schemas were embedded. Update the revision and rebuild when model weights change." };
  }
  keyword(entries, query, limit) {
    const needle = query.toLocaleLowerCase();
    const tokens = needle.split(/\s+/).filter(Boolean);
    const hits = entries.map(entry => {
      const haystack = document(entry).toLocaleLowerCase();
      let score = entry.api_id.toLocaleLowerCase() === needle ? 1000 : 0;
      if (haystack.includes(needle)) score += 10;
      for (const token of tokens) if (haystack.includes(token)) score += 1;
      return { entry, score };
    }).filter(hit => hit.score > 0).sort((a, b) => b.score - a.score || a.entry.api_id.localeCompare(b.entry.api_id));
    return { ok: true, method: "keyword", total: hits.length,
      results: hits.slice(0, limit).map(hit => brief(hit.entry, hit.score)) };
  }
  async search(entries, query, mode, limit) {
    if (!query?.trim()) throw new InputError("Provide a nonempty API search query.");
    const exact = entries.find(entry => entry.api_id === query);
    if (exact) return { ok: true, method: "exact_id", results: [brief(exact, 1)], total: 1 };
    if (mode === "keyword" || (mode === "auto" && !process.env.CST_EMBEDDING_MODEL)) return this.keyword(entries, query, limit);
    try {
      const config = this.configuration();
      const index = readJson(this.store.path("vectors/index.json"), 32 * 1024 * 1024);
      if (index.schema_version !== "cstapi.vector-index.v1" || index.model_identity !== config.identity ||
          index.catalog_fingerprint !== digest(entries)) throw new InputError("Vector index is stale. Run api.reindex explicitly.");
      const vectors = new Map(index.entries.map(entry => [entry.api_id, normalize(entry.vector)]));
      const [queryVector] = await this.embed([query], config);
      const hits = entries.map(entry => {
        const vector = vectors.get(entry.api_id);
        if (!vector || vector.length !== queryVector.length) throw new InputError("Vector index has incompatible entries.");
        return brief(entry, vector.reduce((score, value, index) => score + value * queryVector[index], 0));
      }).sort((a, b) => b.score - a.score || a.api_id.localeCompare(b.api_id));
      return { ok: true, method: "local_vector", model_revision: config.revision,
        results: hits.slice(0, limit), total: hits.length };
    } catch (error) {
      if (mode !== "auto") throw error;
      return { ...this.keyword(entries, query, limit),
        warning: "Vector retrieval was unavailable; explicitly fell back to keyword search. " + error.message };
    }
  }
}
