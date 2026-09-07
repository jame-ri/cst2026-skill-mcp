const text = { type: "string", minLength: 1 };
const id = { type: "string", pattern: "^[a-f0-9-]{36}$" };
const execute = { type: "boolean", default: false };
const timeout = { type: "integer", minimum: 5, maximum: 600, default: 120 };
const session = { session_id: id };
const project = { ...session, project_id: id };
function tool(name, description, properties, required = []) {
  return { name, description, inputSchema: { type: "object",
    properties: { ...properties, execute, timeout_sec: timeout },
    required, additionalProperties: false } };
}
export const directTools = [
  tool("cst.connect", "Connect directly to one explicit local CST instance, or explicitly create one. No document or template lookup. Returns a session_id. Defaults to plan-only.",
    { mode: { type: "string", enum: ["existing", "new"], default: "existing" },
      pid: { type: "integer", minimum: 1 }, operation_id: id }),
  tool("cst.disconnect", "Release this direct connection without saving projects, closing CST, or stopping solvers.",
    { ...session, operation_id: id }, ["session_id"]),
  tool("cst.session_status", "Read direct connection health and bound projects from CST.",
    session, ["session_id"]),
  tool("cst.open_project", "Open or bind an exact repository-relative CST project in the selected session. Returns project_id; does not save.",
    { ...session, project_path: text, require_open: { type: "boolean", default: false }, operation_id: id },
    ["session_id", "project_path"]),
  tool("cst.get_parameters", "Read current CST parameter expressions and available evaluated numeric values directly. Omit names to enumerate.",
    { ...project, names: { type: "array", items: text, minItems: 1, maxItems: 1000 } },
    ["session_id", "project_id"]),
  tool("cst.set_parameters", "Set named CST parameters directly, with a named History entry and optional rebuild. Does not save; failures may leave partial changes.",
    { ...project, parameters: { type: "object" }, create_missing: { type: "boolean", default: false },
      rebuild: { type: "boolean", default: true }, operation_id: id },
    ["session_id", "project_id", "parameters"]),
  tool("cst.save_project", "Save a project copy without closing, or explicitly save the original. Save As changes the bound filename.",
    { ...project, save_policy: { type: "string", enum: ["save_copy", "save_original"], default: "save_copy" },
      save_copy_path: text, include_results: { type: "boolean", default: true },
      allow_overwrite: { type: "boolean", default: false }, operation_id: id },
    ["session_id", "project_id"]),
  tool("cst.run_solver", "Start the currently configured CST solver asynchronously. Requires execute=true and allow_solve=true; returns job_id, not verified simulation success.",
    { ...project, allow_solve: { type: "boolean", default: false }, operation_id: id },
    ["session_id", "project_id"]),
  tool("cst.solver_status", "Query actual CST solver state and run information. A non-running solver is not proof of successful or physically valid results.",
    { ...project, job_id: id }, ["session_id", "project_id"]),
  tool("cst.stop_solver", "Request cancellation of the exact solver job started by this session. Never kills processes by name.",
    { ...project, job_id: id, allow_stop: { type: "boolean", default: false }, operation_id: id },
    ["session_id", "project_id", "job_id"]),
  tool("cst.list_results", "List 0D/1D result-tree paths for the selected saved project through cst.results; no knowledge lookup.",
    { ...project, module: { type: "string", enum: ["3d", "schematic"], default: "3d" },
      query: { type: "string" }, offset: { type: "integer", minimum: 0, maximum: 1000000, default: 0 },
      limit: { type: "integer", minimum: 1, maximum: 1000, default: 100 } },
    ["session_id", "project_id"]),
  tool("cst.read_result", "Read a specific 0D/1D result and run_id, returning paged samples, axis labels and explicit complex values. Freshness/physics are not automatically certified.",
    { ...project, module: { type: "string", enum: ["3d", "schematic"], default: "3d" },
      tree_path: text, run_id: { type: "integer", minimum: 0, maximum: 1000000 },
      offset: { type: "integer", minimum: 0, maximum: 10000000, default: 0 },
      limit: { type: "integer", minimum: 1, maximum: 10000, default: 2000 } },
    ["session_id", "project_id", "tree_path", "run_id"])
];
