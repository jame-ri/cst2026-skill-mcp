"""Direct, session-bound CST operations. No retrieval or arbitrary-code tool.

API sources checked during implementation:
official-docs/python/source/cst.interface.html
official-docs/python/source/cst.results.html
official-docs/vba-3d/common_vbaapp/common_vbaappapplication_object.htm
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path, PureWindowsPath
import re
import sys
import tempfile
from datetime import datetime, timezone
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


class CstError(RuntimeError):
    def __init__(self, code, message, **details):
        super().__init__(message)
        self.code = code
        self.details = details


def now():
    return datetime.now(timezone.utc).isoformat()


def contained(value):
    if not isinstance(value, str) or not value or any(ord(c) < 32 for c in value):
        raise CstError("invalid_path", "Use a nonempty repository-relative path.")
    win = PureWindowsPath(value)
    relative = Path(value.replace("\\", "/"))
    if win.drive or win.root or relative.is_absolute() or ":" in value:
        raise CstError("invalid_path", "Absolute, drive and device paths are not allowed.")
    if any(part in {"", ".", ".."} for part in value.replace("\\", "/").split("/")):
        raise CstError("invalid_path", "Dot segments and empty path components are not allowed.")
    target = ROOT
    for part in relative.parts:
        if part.endswith((" ", ".")) or re.fullmatch(r"(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?", part):
            raise CstError("invalid_path", "Reserved path component.")
        target = target / part
        try:
            stat = target.lstat()
            if target.is_symlink() or getattr(stat, "st_file_attributes", 0) & 0x400:
                raise CstError("invalid_path", "Symlinks and junctions are not allowed.")
        except FileNotFoundError:
            pass
    resolved = target.resolve()
    if not resolved.is_relative_to(ROOT):
        raise CstError("invalid_path", "Path must remain inside the repository.")
    return resolved


def relative_name(value):
    resolved = Path(value).resolve()
    if not resolved.is_relative_to(ROOT):
        raise CstError("outside_repository", "The selected project is outside the repository.")
    return resolved.relative_to(ROOT).as_posix()


def same_path(left, right):
    return os.path.normcase(os.path.abspath(left)) == os.path.normcase(os.path.abspath(right))


def clean(value):
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else {"non_finite": str(value)}
    if isinstance(value, complex):
        return {"real": clean(value.real), "imag": clean(value.imag)}
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if hasattr(value, "tolist"):
        return clean(value.tolist())
    if hasattr(value, "item"):
        return clean(value.item())
    return str(value)


def vba_string(value):
    value = str(value)
    if any(ord(c) < 32 for c in value):
        raise CstError("invalid_parameter", "VBA string inputs must be single-line.")
    return '"' + value.replace('"', '""') + '"'


class DirectCst:
    def __init__(self):
        self.de = None
        self.session_id = None
        self.projects = {}
        self.jobs = {}
        self.lease = None
        self.lease_token = None
        self.effect_started = False
        self.context = {}

    def acquire(self, pid):
        root = Path(tempfile.gettempdir()) / "cst2026-mcp-leases"
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        if root.is_symlink() or getattr(root.lstat(), "st_file_attributes", 0) & 0x400:
            raise CstError("unsafe_lease_root", "The runtime lease directory must not be a link.")
        file = root / ("pid-" + str(pid) + ".json")
        token = str(uuid4())
        try:
            with file.open("x", encoding="utf-8") as stream:
                json.dump({"cst_pid": pid, "worker_pid": os.getpid(), "token": token, "created_at": now()}, stream)
                stream.flush()
                os.fsync(stream.fileno())
        except FileExistsError:
            raise CstError("instance_leased", "Another direct controller owns this CST PID, or a stale lease remains. Inspect its owner before manual cleanup.", pid=pid)
        self.lease = file
        self.lease_token = token

    def release(self):
        if self.lease:
            try:
                data = json.loads(self.lease.read_text(encoding="utf-8"))
                if data.get("token") == self.lease_token:
                    self.lease.unlink()
            except FileNotFoundError:
                pass
            finally:
                self.lease = None
                self.lease_token = None

    def session(self, args):
        if not self.de or args.get("session_id") != self.session_id:
            raise CstError("invalid_session", "Connect first and use the returned session_id.")
        if not self.de.is_connected():
            raise CstError("disconnected", "CST connection was lost. Disconnect and reconnect explicitly.")
        return self.de

    def project(self, args):
        self.session(args)
        entry = self.projects.get(args.get("project_id"))
        if not entry:
            raise CstError("invalid_project", "Open/bind the project first and use its project_id.")
        handle = entry["handle"]
        actual = handle.filename()
        if not actual or not same_path(actual, entry["path"]):
            raise CstError("project_binding_changed", "The project filename changed outside this controller; bind it again.")
        # Fail if the project was closed externally instead of silently reopening.
        self.de.get_open_project(entry["path"])
        return entry

    @staticmethod
    def idle(entry):
        if entry["handle"].model3d.is_solver_running():
            raise CstError("solver_busy", "This project is solving. Do not modify or save it until the solve stops.")

    def connect(self, args):
        if self.de:
            raise CstError("already_connected", "Disconnect the existing session before selecting another instance.", session_id=self.session_id)
        from .environment import configure
        configure()
        import cst.interface as interface
        mode = args.get("mode", "existing")
        if mode == "existing":
            pids = [int(pid) for pid in interface.running_design_environments()]
            pid = args.get("pid")
            if pid is None:
                if len(pids) != 1:
                    raise CstError("select_instance", "Specify a PID, or explicitly request mode=new. No instance was created.", available_pids=pids)
                pid = pids[0]
            if pid not in pids:
                raise CstError("instance_not_found", "The requested PID is not a running CST instance.", available_pids=pids)
            self.acquire(pid)
            try:
                de = interface.DesignEnvironment.connect(pid)
            except Exception:
                self.release()
                raise
            owned = False
        elif mode == "new":
            self.effect_started = True
            de = interface.DesignEnvironment.new()
            pid = int(de.pid())
            self.context = {"created_cst_pid": pid}
            self.acquire(pid)
            owned = True
        else:
            raise CstError("invalid_mode", "Connection mode must be existing or new.")
        self.de = de
        self.session_id = str(uuid4())
        self.projects = {}
        self.jobs = {}
        return {"status": "connected", "session_id": self.session_id,
                "pid": int(de.pid()), "created_by_controller": owned,
                "projects": self.project_paths(),
                "note": "This session is exclusive to cooperating direct controllers. No project was opened or saved."}

    def project_paths(self):
        result = []
        for name in self.de.list_open_projects():
            try:
                relative = relative_name(name)
                contained(relative)
                result.append({"project_path": relative, "operable": True})
            except CstError:
                result.append({"display_name": Path(name).name, "operable": False, "reason": "outside_or_unbound_path"})
        return result

    def session_status(self, args):
        de = self.session(args)
        return {"status": "connected", "session_id": self.session_id, "pid": int(de.pid()),
                "projects": self.project_paths(),
                "bindings": [{"project_id": key, "project_path": relative_name(item["path"])}
                             for key, item in self.projects.items()]}

    def disconnect(self, args):
        self.session(args)
        pid = int(self.de.pid())
        self.release()
        # Deliberately never call Project.close() or DesignEnvironment.close().
        self.projects = {}
        self.jobs = {}
        self.de = None
        self.session_id = None
        return {"status": "disconnected", "pid": pid, "cst_closed": False,
                "projects_saved": False, "solvers_stopped": False,
                "note": "Any running CST solver continues outside this released session."}

    def open_project(self, args):
        de = self.session(args)
        target = contained(args["project_path"])
        if target.suffix.lower() != ".cst" or not target.is_file():
            raise CstError("project_not_found", "Provide an existing .cst project inside the repository.")
        for entry in self.projects.values():
            self.idle(entry)
        matching = next((name for name in de.list_open_projects() if same_path(name, target)), None)
        if matching:
            handle = de.get_open_project(matching)
        else:
            if args.get("require_open", False):
                raise CstError("project_not_open", "The project is not open in this selected instance.")
            self.effect_started = True
            handle = de.open_project(str(target))
        actual = contained(relative_name(handle.filename()))
        if not same_path(actual, target):
            raise CstError("project_mismatch", "CST returned a different project than requested.")
        for project_id, entry in self.projects.items():
            if same_path(entry["path"], actual):
                entry["handle"] = handle
                return {"status": "bound", "project_id": project_id, "project_path": relative_name(actual)}
        project_id = str(uuid4())
        self.projects[project_id] = {"handle": handle, "path": str(actual), "dirty_by_controller": False}
        return {"status": "bound", "project_id": project_id, "project_path": relative_name(actual)}

    def parameters(self, entry):
        root = contained("design-records/.cst-runtime")
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="parameters-", dir=root) as temporary:
            output = Path(temporary) / "parameters.tsv"
            # Unicode strings are emitted as UTF-16 code-unit hex, independent
            # of the CST VBA host's ANSI file encoding.
            code = "\n".join([
                "Sub Main",
                "Dim f As Integer, i As Long, n As Long, opened As Boolean",
                "Dim numericText As String, errorCode As Long, errorText As String",
                "On Error GoTo Failed",
                "n = GetNumberOfParameters",
                'If n > 10000 Then Err.Raise 1001, "CST MCP", "Too many parameters"',
                "f = FreeFile",
                "Open " + vba_string(output) + " For Output As #f",
                "opened = True",
                "For i = 0 To n - 1",
                'numericText = ""',
                "On Error Resume Next",
                "numericText = Trim$(Str$(GetParameterNValue(i)))",
                'If Err.Number <> 0 Then numericText = ""',
                "Err.Clear",
                "On Error GoTo Failed",
                "Print #f, CstHex(GetParameterName(i)) & vbTab & CstHex(GetParameterSValue(i)) & vbTab & numericText",
                "Next i",
                'Print #f, "__CST_PARAMETERS_COMPLETE__"',
                "Close #f",
                "Exit Sub",
                "Failed:",
                "errorCode = Err.Number",
                "errorText = Err.Description",
                "On Error Resume Next",
                "If opened Then Close #f",
                "On Error GoTo 0",
                'Err.Raise errorCode, "CST MCP parameter read", errorText',
                "End Sub",
                "Function CstHex(ByVal value As String) As String",
                "Dim j As Long, c As Long, result As String",
                'result = ""',
                "For j = 1 To Len(value)",
                "c = AscW(Mid$(value, j, 1))",
                "If c < 0 Then c = c + 65536",
                'result = result & Right$("0000" & Hex$(c), 4)',
                "Next j",
                "CstHex = result",
                "End Function",
            ])
            entry["handle"].schematic.execute_vba_code(code)
            if not output.is_file() or output.stat().st_size > 16 * 1024 * 1024:
                raise CstError("parameter_read_failed", "CST did not produce a bounded parameter snapshot.")
            lines = output.read_text(encoding="ascii").splitlines()
            if not lines or lines[-1] != "__CST_PARAMETERS_COMPLETE__":
                raise CstError("parameter_read_failed", "CST parameter snapshot was incomplete.")
            result = []
            for line in lines[:-1]:
                name, expression, numeric = line.split("\t")
                try:
                    value = float(numeric) if numeric else None
                except ValueError:
                    value = None
                result.append({"name": bytes.fromhex(name).decode("utf-16-be"),
                               "expression": bytes.fromhex(expression).decode("utf-16-be"),
                               "value": clean(value), "numeric_available": value is not None})
            return result

    def get_parameters(self, args):
        entry = self.project(args)
        parameters = self.parameters(entry)
        if args.get("names"):
            wanted = set(args["names"])
            found = {row["name"] for row in parameters}
            if wanted - found:
                raise CstError("parameter_not_found", "Some requested parameter names do not exist.", missing=sorted(wanted - found))
            parameters = [row for row in parameters if row["name"] in wanted]
        return {"status": "read", "project_id": args["project_id"], "parameters": parameters,
                "source": "live_cst_parameters", "observed_at": now()}

    def set_parameters(self, args):
        entry = self.project(args)
        self.idle(entry)
        requested = args["parameters"]
        if not isinstance(requested, dict) or not 1 <= len(requested) <= 100:
            raise CstError("invalid_parameters", "Provide 1-100 parameter values.")
        before = self.parameters(entry)
        known = {row["name"].casefold(): row["name"] for row in before}
        names = set()
        assignments = []
        for name, value in requested.items():
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) or name.casefold() in names:
                raise CstError("invalid_parameters", "Names must be distinct CST identifiers.")
            names.add(name.casefold())
            if isinstance(value, bool) or not isinstance(value, (str, int, float)):
                raise CstError("invalid_parameters", "Values must be expressions or numbers.")
            if isinstance(value, float) and not math.isfinite(value):
                raise CstError("invalid_parameters", "Numeric values must be finite.")
            if not str(value).strip() or len(str(value)) > 4096:
                raise CstError("invalid_parameters", "Empty or oversized expression.")
            actual = known.get(name.casefold())
            if actual is None and not args.get("create_missing", False):
                raise CstError("parameter_not_found", "Parameter creation requires create_missing=true.", parameter=name)
            actual = actual or name
            assignments.append("StoreParameter " + vba_string(actual) + ", " + vba_string(value))
        caption = "MCP parameters " + args["operation_id"]
        self.effect_started = True
        entry["dirty_by_controller"] = True
        entry["handle"].model3d.add_to_history(caption, "\n".join(assignments))
        rebuilt = args.get("rebuild", True)
        if rebuilt:
            entry["handle"].model3d.full_history_rebuild()
        after = self.parameters(entry)
        return {"status": "parameters_updated", "project_id": args["project_id"],
                "before": [row for row in before if row["name"].casefold() in names],
                "after": [row for row in after if row["name"].casefold() in names],
                "history_caption": caption, "model_rebuilt": rebuilt, "saved": False,
                "results_require_new_solve": True, "physics_validated": False}

    def save_project(self, args):
        entry = self.project(args)
        self.idle(entry)
        original = Path(entry["path"])
        policy = args.get("save_policy", "save_copy")
        if policy == "save_copy":
            destination = contained(args["save_copy_path"])
            if destination.suffix.lower() != ".cst" or same_path(destination, original):
                raise CstError("invalid_save_copy", "A copy must use a different .cst filename.")
        elif policy == "save_original":
            destination = original
        else:
            raise CstError("invalid_save_policy", "Use save_copy or save_original.")
        if policy == "save_copy" and destination.exists() and not args.get("allow_overwrite", False):
            raise CstError("file_exists", "The copy destination exists; overwrite was not authorized.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        self.effect_started = True
        entry["handle"].save(str(destination), args.get("include_results", True), args.get("allow_overwrite", False))
        actual = contained(relative_name(entry["handle"].filename()))
        entry["path"] = str(actual)
        entry["dirty_by_controller"] = False
        return {"status": "saved", "project_id": args["project_id"], "save_policy": policy,
                "requested_path": relative_name(destination), "bound_project_path": relative_name(actual),
                "project_closed": False, "note": "Save As may change the filename of the open project."}

    def run_solver(self, args):
        if args.get("allow_solve") is not True:
            raise CstError("solve_not_authorized", "Set allow_solve=true only for a user-authorized solve.")
        entry = self.project(args)
        self.idle(entry)
        model = entry["handle"].model3d
        solver = model.get_active_solver_name()
        parameters = self.parameters(entry)
        job_id = str(uuid4())
        job = {"job_id": job_id, "project_id": args["project_id"], "project_path": relative_name(entry["path"]),
               "submitted_at": now(), "solver": solver, "parameters": parameters,
               "active": True, "stop_requested": False}
        self.jobs[args["project_id"]] = job
        self.context = {"job_id": job_id}
        self.effect_started = True
        # Official non-blocking API. Do not call blocking run_solver() here.
        model.start_solver()
        return {"status": "submitted", **job, "physics_validated": False,
                "note": "Only the configured solver was started. Poll solver_status; a submitted job is not a successful result."}

    def solver_status(self, args):
        entry = self.project(args)
        job = self.jobs.get(args["project_id"])
        if args.get("job_id") and (not job or job["job_id"] != args["job_id"]):
            raise CstError("job_mismatch", "The job_id does not belong to this bound project/session.")
        model = entry["handle"].model3d
        running = bool(model.is_solver_running())
        info = clean(model.get_solver_run_info())
        if job and not running:
            job["active"] = False
        status = "running" if running else "not_running"
        return {"status": status, "running": running, "job_id": job["job_id"] if job else None,
                "tracked_by_session": job is not None, "run_info": info,
                "stop_requested": job["stop_requested"] if job else False,
                "observed_at": now(), "success_verified": False,
                "note": "not_running does not prove convergence, success, or fresh results. Inspect run_info and the selected result run."}

    def stop_solver(self, args):
        if args.get("allow_stop") is not True:
            raise CstError("stop_not_authorized", "Set allow_stop=true only for a user-authorized stop.")
        entry = self.project(args)
        job = self.jobs.get(args["project_id"])
        if not job or job["job_id"] != args["job_id"] or not job["active"]:
            raise CstError("job_mismatch", "Only this session's still-active tracked job may be stopped.")
        model = entry["handle"].model3d
        if not model.is_solver_running():
            job["active"] = False
            return {"status": "not_running", "job_id": job["job_id"], "stop_requested": False}
        self.effect_started = True
        job["stop_requested"] = True
        model.abort_solver()
        return {"status": "stop_requested", "job_id": job["job_id"],
                "note": "Query solver_status to confirm no solver is running. No CST process was killed."}

    def results_module(self, args):
        entry = self.project(args)
        self.idle(entry)
        if not Path(entry["path"]).is_file():
            raise CstError("unsaved_project", "Save the project before reading its result file.")
        import cst.results as results
        project_file = results.ProjectFile(entry["path"], allow_interactive=True)
        module = project_file.get_3d() if args.get("module", "3d") == "3d" else project_file.get_schematic()
        return entry, project_file, module

    def list_results(self, args):
        entry, project_file, module = self.results_module(args)
        paths = [str(value) for value in module.get_tree_items("0D/1D")]
        query = args.get("query", "").casefold()
        if query:
            paths = [value for value in paths if query in value.casefold()]
        offset, limit = args.get("offset", 0), args.get("limit", 100)
        page = paths[offset:offset + limit]
        return {"status": "read", "project_path": relative_name(entry["path"]), "result_type": "0D/1D",
                "tree_paths": page, "total": len(paths), "offset": offset,
                "next_offset": offset + len(page) if offset + len(page) < len(paths) else None,
                "freshness": "not_verified"}

    def read_result(self, args):
        entry, project_file, module = self.results_module(args)
        item = module.get_result_item(args["tree_path"], run_id=args["run_id"], load_impedances=False)
        metadata = {}
        for key in ("title", "treepath", "xlabel", "ylabel"):
            value = getattr(item, key)
            metadata[key] = clean(value() if callable(value) else value)
        data = item.get_data()
        offset, limit = args.get("offset", 0), args.get("limit", 2000)
        if isinstance(data, (int, float, complex)):
            payload = {"result_type": "0D", "value": clean(data), "point_count": 1}
        else:
            xs, ys = item.get_xdata(), item.get_ydata()
            count = len(ys)
            if len(xs) != count:
                raise CstError("result_shape_mismatch", "CST returned unequal x/y sample lengths.")
            payload = {"result_type": "1D", "point_count": count, "offset": offset,
                       "x": clean(xs[offset:offset + limit]), "y": clean(ys[offset:offset + limit]),
                       "next_offset": offset + limit if offset + limit < count else None}
        return {"status": "read", **metadata, **payload, "project_path": relative_name(entry["path"]),
                "run_id": args["run_id"], "source": "cst.results", "freshness": "not_verified",
                "dirty_by_controller": entry["dirty_by_controller"], "complex_encoding": "{real, imag}",
                "note": "Axis labels are returned as supplied by CST; no implicit GHz/dB conversion or physical-validity claim."}

    def dispatch(self, method, args):
        from .extensions import execute_extension
        methods = {
            "api.extension": lambda payload: execute_extension(self, payload),
            "cst.connect": self.connect, "cst.disconnect": self.disconnect,
            "cst.session_status": self.session_status, "cst.open_project": self.open_project,
            "cst.get_parameters": self.get_parameters, "cst.set_parameters": self.set_parameters,
            "cst.save_project": self.save_project, "cst.run_solver": self.run_solver,
            "cst.solver_status": self.solver_status, "cst.stop_solver": self.stop_solver,
            "cst.list_results": self.list_results, "cst.read_result": self.read_result,
        }
        self.effect_started = False
        self.context = {}
        try:
            if args.get("execute") is not True:
                raise CstError("execute_required", "The worker only accepts explicit execution.")
            if method not in methods:
                raise CstError("unknown_operation", "Unsupported direct CST operation.")
            return {"ok": True, **methods[method](args)}
        except Exception as error:
            return {"ok": False, "status": "unknown_outcome" if self.effect_started else "failed",
                    "error": getattr(error, "code", "cst_api_error"), "message": str(error),
                    "state_may_have_changed": self.effect_started, **self.context,
                    **getattr(error, "details", {})}


def main():
    # Keep a private protocol descriptor; native CST writes to stdout are
    # redirected to stderr as well as ordinary Python prints.
    protocol = os.fdopen(os.dup(sys.stdout.fileno()), "w", encoding="utf-8", buffering=1, newline="\n")
    os.dup2(sys.stderr.fileno(), sys.stdout.fileno())
    controller = DirectCst()
    try:
        while True:
            line = sys.stdin.buffer.readline(2 * 1024 * 1024 + 1)
            if not line:
                break
            request_id = None
            try:
                if len(line) > 2 * 1024 * 1024:
                    raise ValueError("Worker input exceeds its limit.")
                request = json.loads(line)
                request_id = request["id"]
                result = controller.dispatch(request["method"], request["args"])
            except Exception as error:
                result = {"ok": False, "status": "failed", "error": "worker_protocol_error", "message": str(error)}
            protocol.write(json.dumps({"id": request_id, "result": clean(result)}, ensure_ascii=False, allow_nan=False) + "\n")
            protocol.flush()
    finally:
        controller.release()
        protocol.close()


if __name__ == "__main__":
    main()
