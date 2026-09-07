const text = { type: "string", minLength: 1 };
const execute = { type: "boolean", default: false };
const argumentsObject = { type: "object" };
function tool(name, description, properties, required = []) {
  return { name, description, inputSchema: { type: "object", properties, required, additionalProperties: false } };
}
export const apiTools = [
  tool("api.search", "Discover callable CST APIs, not arbitrary knowledge snippets. Exact IDs bypass retrieval; optional local vectors assist only discovery.",
    { query: { ...text, maxLength: 500 }, mode: { type: "string", enum: ["auto", "keyword", "vector"], default: "auto" },
      limit: { type: "integer", minimum: 1, maximum: 50, default: 10 } }, ["query"]),
  tool("api.describe", "Return an exact API's input schema, status and provenance. Bundled APIs and locally verified extensions are distinguished.",
    { api_id: text }, ["api_id"]),
  tool("api.call", "Invoke a known CST API by exact ID; no document or vector lookup. Execution gates are inside arguments. Use api.describe for its schema.",
    { api_id: text, arguments: argumentsObject }, ["api_id", "arguments"]),
  tool("api.stage", "Snapshot a repository-relative candidate JSON and its Python source. Does not execute code or mark it verified. Requires execute=true to write.",
    { candidate_path: text, execute }, ["candidate_path"]),
  tool("api.trial", "Run a staged Python API once with explicit authorization and its postcondition verifier. A passing durable receipt can automatically register this exact version.",
    { candidate_id: { type: "string", pattern: "^[a-f0-9]{64}$" }, arguments: argumentsObject,
      promote_on_pass: { type: "boolean", default: true } }, ["candidate_id", "arguments"]),
  tool("api.retire", "Disable a registered local API without deleting its source or execution evidence. Requires execute=true; use a new version for repairs.",
    { api_id: text, reason: { ...text, maxLength: 2000 }, execute }, ["api_id", "reason"]),
  tool("api.reindex", "Explicitly build a local vector index of active API descriptions using a preconfigured local model. Never installs dependencies or downloads model weights.",
    { execute })
];

export async function callApiTool(registry, name, args) {
  switch (name) {
    case "api.search": return registry.search(args);
    case "api.describe": return registry.describe(args.api_id);
    case "api.call": return registry.call(args.api_id, args.arguments);
    case "api.stage": return registry.stage(args);
    case "api.trial": return registry.trial(args);
    case "api.retire": return registry.retire(args);
    case "api.reindex": return registry.reindex(args);
    default: throw new Error("Unknown API library tool.");
  }
}
