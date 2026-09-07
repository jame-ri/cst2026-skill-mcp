import { containedPath } from "../shared/paths.js";
import { InputError, validateArguments } from "../shared/runtime.js";
import { portableRecord } from "../shared/data.js";
import { ExecutionJournal } from "../harness/journal.js";
import { CstWorkerClient } from "./worker-client.js";
import { directTools } from "./catalog.js";

const journaled = new Set(["cst.connect", "cst.disconnect", "cst.open_project", "cst.set_parameters",
  "cst.save_project", "cst.run_solver", "cst.stop_solver", "api.extension"]);

export class CstController {
  constructor(repoRoot, pythonExecutable) {
    this.repoRoot = repoRoot;
    this.names = new Set(directTools.map(tool => tool.name));
    this.worker = new CstWorkerClient(repoRoot, pythonExecutable);
    this.journal = new ExecutionJournal(repoRoot);
    this.active = false;
    this.sessionId = null;
    this.busy = false;
  }
  validate(name, args) {
    const tool = directTools.find(item => item.name === name);
    if (tool) validateArguments(args, tool.inputSchema);
    else if (name !== "api.extension") throw new InputError("Unknown CST API.");
    if (name === "cst.connect" && args.mode === "new" && args.pid !== undefined) throw new InputError("mode=new cannot specify an existing PID.");
    for (const key of ["project_path", "save_copy_path", "source_path"]) if (args[key]) containedPath(this.repoRoot, args[key]);
    if (args.project_path && !args.project_path.toLowerCase().endsWith(".cst")) throw new InputError("project_path must end with .cst.");
    if (name === "cst.save_project") {
      if ((args.save_policy ?? "save_copy") === "save_copy" && !args.save_copy_path) throw new InputError("save_copy requires save_copy_path.");
      if (args.save_policy === "save_original" && args.save_copy_path) throw new InputError("save_original cannot specify save_copy_path.");
      if (args.save_copy_path && !args.save_copy_path.toLowerCase().endsWith(".cst")) throw new InputError("save_copy_path must end with .cst.");
    }
    if (name === "cst.set_parameters") {
      const entries = Object.entries(args.parameters);
      if (!entries.length || entries.length > 100) throw new InputError("Provide 1-100 parameter values.");
      for (const [key, value] of entries) {
        if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(key)) throw new InputError("Parameter names must be ASCII CST identifiers.");
        if (!["number", "string"].includes(typeof value) || (typeof value === "number" && !Number.isFinite(value)) ||
            (typeof value === "string" && (!value.trim() || value.length > 4096 || /[\u0000-\u001f\u007f]/.test(value)))) {
          throw new InputError("Parameter values must be finite numbers or single-line expressions.");
        }
      }
    }
    if (args.execute === true && name === "cst.run_solver" && args.allow_solve !== true) throw new InputError("Solver execution requires allow_solve=true and user authorization.");
    if (args.execute === true && name === "cst.stop_solver" && args.allow_stop !== true) throw new InputError("Solver cancellation requires allow_stop=true and user authorization.");
  }
  async dispatch(name, args) {
    try {
      const result = await this.worker.call(name, args, (args.timeout_sec ?? 120) * 1000);
      if (name === "cst.connect" && result.ok) { this.active = true; this.sessionId = result.session_id; }
      if (name === "cst.disconnect" && result.ok) { this.active = false; this.sessionId = null; }
      return portableRecord(this.repoRoot, { execute: true, ...result });
    } catch (error) {
      if (!this.worker.child) { this.active = false; this.sessionId = null; }
      return portableRecord(this.repoRoot, { execute: true, ok: false, status: "unknown_outcome",
        message: error.message, state_may_have_changed: journaled.has(name),
        recovery: "Inspect CST before retrying. A lost worker invalidates its session IDs; never replay uncertain mutations." });
    }
  }
  async call(name, args) {
    this.validate(name, args);
    if (args.execute !== true) return { execute: false, ok: true, status: "planned", api_id: name,
      arguments: args, note: "No CST execution, document lookup or template search." };
    if (this.busy) throw new InputError("The CST controller is busy. No action was dispatched.");
    this.busy = true;
    try {
      const result = journaled.has(name)
        ? await this.journal.run(name, args, payload => this.dispatch(name, payload))
        : await this.dispatch(name, args);
      if (result.replayed && ((name === "cst.connect" && result.session_id !== this.sessionId) ||
          (name === "cst.open_project" && args.session_id !== this.sessionId))) {
        return { ...result, ok: false, status: "historical_receipt",
          message: "This is a historical receipt, not a live binding. Connect and bind explicitly with new operation IDs." };
      }
      return result;
    } finally { this.busy = false; }
  }
  stop() { this.worker.stop(); this.active = false; this.sessionId = null; }
}
