import { directTools } from "../cst_api/catalog.js";
import { InputError, validateArguments } from "../shared/runtime.js";
import { assertPortable } from "../shared/data.js";
import { containedPath } from "../shared/paths.js";
import { extensionSchema, validateInput } from "./schema.js";
import { ApiStore } from "./storage.js";
import { ApiVectorSearch } from "./vector-search.js";

export class ApiRegistry {
  constructor(root, controller) {
    this.root = root;
    this.controller = controller;
    this.store = new ApiStore(root);
    this.vectors = new ApiVectorSearch(root, this.store);
  }
  builtin(name) { return directTools.find(tool => tool.name === name); }
  descriptors() {
    const bundled = directTools.map(tool => ({ api_id: tool.name, description: tool.description,
      input_schema: tool.inputSchema, status: "bundled", source: "cst_api/worker.py",
      validation: "Bundled implementation; live CST validation is not implied by catalog membership." }));
    const registered = this.store.list().filter(item => item.status === "locally_verified").map(item => this.describeRegistration(item));
    return [...bundled, ...registered];
  }
  describeRegistration(item) {
    const definition = item.candidate.definition;
    return { api_id: item.api_id, description: definition.description,
      input_schema: extensionSchema(definition), effect: definition.effect,
      cst_version: definition.cst_version, tags: definition.tags,
      status: item.status, candidate_id: item.candidate_id,
      implementation_sha256: item.candidate.implementation_sha256,
      references: item.candidate.source_references, receipt_path: item.receipt_path,
      callable: item.status === "locally_verified",
      extension_execution_enabled: process.env.CST_ENABLE_API_EXTENSIONS === "1",
      warning: "Local Python extensions are reviewed executable code, not sandboxed knowledge snippets." };
  }
  describe(apiId) {
    const builtin = this.builtin(apiId);
    if (builtin) return { ok: true, api_id: apiId, description: builtin.description,
      input_schema: builtin.inputSchema, status: "bundled", callable: true,
      validation: "Use actual execution evidence; bundled does not mean tested in your CST installation." };
    const registration = this.store.registration(apiId);
    if (!registration) throw new InputError("API not found. Search the catalog; missing APIs must be staged and trialed before registration.");
    return { ok: true, ...this.describeRegistration(registration) };
  }
  async search(args) {
    const entries = this.descriptors();
    return this.vectors.search(entries, args.query, args.mode ?? "auto", args.limit ?? 10);
  }
  extensionPayload(candidate, args) {
    const definition = candidate.definition;
    validateArguments(args, extensionSchema(definition));
    validateInput(args.parameters, definition.input_schema);
    if (args.execute === true) {
      if (process.env.CST_ENABLE_API_EXTENSIONS !== "1" || args.allow_extension_execution !== true) throw new InputError("Extensions require CST_ENABLE_API_EXTENSIONS=1 and allow_extension_execution=true after code review.");
      if (definition.effect === "solve" && args.allow_solve !== true) throw new InputError("A solver extension requires allow_solve=true.");
    }
    return { ...args, api_id: this.store.apiId(candidate), candidate_id: candidate.candidate_id,
      source_path: candidate.source_path, implementation_sha256: candidate.implementation_sha256,
      entrypoint: definition.entrypoint, verifier: definition.verifier,
      cst_version: definition.cst_version, effect: definition.effect };
  }
  async call(apiId, args) {
    if (this.builtin(apiId)) return this.controller.call(apiId, args);
    const registration = this.store.registration(apiId);
    if (!registration || registration.status !== "locally_verified") throw new InputError("Only locally verified, active API versions can be called. Candidates need api.trial.");
    const payload = this.extensionPayload(registration.candidate, args);
    const result = await this.controller.call("api.extension", payload);
    if (result.execute && result.verification?.passed === false) {
      try { return { ...result, lifecycle: await this.store.setState(apiId, "disputed", "A later execution failed its verification contract.", result.operation_id) }; }
      catch { return { ...result, warning: "Verification failed and the disputed-state record could not be saved. Do not reuse this API until it is retired or repaired as a new version." }; }
    }
    return result;
  }
  async stage(args) {
    containedPath(this.root, args.candidate_path);
    if (args.execute !== true) return { ok: true, execute: false, status: "planned", candidate_path: args.candidate_path,
      note: "Would snapshot candidate metadata, Python source and source-reference hashes. Nothing was written or executed." };
    return this.store.stage(args.candidate_path);
  }
  async trial(args) {
    const candidate = this.store.candidate(args.candidate_id);
    if (args.promote_on_pass !== false) this.store.preflightPromotion(candidate);
    const result = await this.controller.call("api.extension", this.extensionPayload(candidate, args.arguments));
    if (args.promote_on_pass === false || result.execute !== true || !result.ok || result.verification?.passed !== true) {
      return { ...result, registration: { status: "not_registered" } };
    }
    if (result.record?.status !== "stored") return { ...result, registration: { status: "blocked_missing_receipt" },
      warning: "A passing response without a durable receipt is not sufficient for registration. Do not rerun CST to repair recording." };
    try { return { ...result, registration: await this.store.promote(candidate, result) }; }
    catch (error) { return { ...result, registration: { status: "error", message: error.message },
      warning: "Execution and registration are separate outcomes. Do not repeat the CST action to repair the registry." }; }
  }
  async retire(args) {
    assertPortable(args.reason, "reason");
    if (!this.store.registration(args.api_id)) throw new InputError("Registered extension not found.");
    if (args.execute !== true) return { ok: true, execute: false, status: "planned", api_id: args.api_id };
    return { ok: true, execute: true, ...await this.store.setState(args.api_id, "retired", args.reason) };
  }
  async reindex(args) {
    if (args.execute !== true) return { ok: true, execute: false, status: "planned",
      note: "Would embed active API descriptions with a configured local model. No model is installed or downloaded." };
    return this.vectors.reindex(this.descriptors());
  }
}
