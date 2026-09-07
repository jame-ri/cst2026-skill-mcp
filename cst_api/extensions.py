"""Explicitly authorized local Python extensions. This is NOT a sandbox."""
from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import re
import sys


class ExtensionContext:
    def __init__(self, controller, entry, args, contained, relative_name):
        self.project = entry["handle"]
        self.design_environment = controller.de
        self.project_path = relative_name(entry["path"])
        self._controller = controller
        self._entry = entry
        self._args = args
        self._contained = contained

    def path(self, relative_path):
        """Resolve a workspace-relative path; do not persist the absolute result."""
        return self._contained(relative_path)

    def parameters(self):
        return self._controller.parameters(self._entry)

    def start_solver(self):
        """Use the same tracked solver job mechanism as the built-in API."""
        return self._controller.run_solver(self._args)


def execute_extension(controller, args):
    runtime = sys.modules[type(controller).__module__]
    error = runtime.CstError
    if os.environ.get("CST_ENABLE_API_EXTENSIONS") != "1" or args.get("allow_extension_execution") is not True:
        raise error("extension_not_authorized", "Operator configuration and explicit per-call extension authorization are both required.")
    if args.get("effect") not in {"read", "modify", "solve"}:
        raise error("invalid_extension", "Invalid extension effect.")
    if args["effect"] == "solve" and args.get("allow_solve") is not True:
        raise error("solve_not_authorized", "A solver extension also requires allow_solve=true.")
    entry = controller.project(args)
    controller.idle(entry)
    version = getattr(controller.de, "version", None)
    actual_version = str(version() if callable(version) else version)
    years = re.findall(r"(?<!\d)20\d{2}(?!\d)", actual_version)
    if args.get("cst_version") not in years:
        raise error("extension_version_mismatch", "The actual CST version does not match the candidate's declared year.",
                    actual_cst_version=actual_version, required_cst_version=args.get("cst_version"))
    source = runtime.contained(args["source_path"])
    if source.suffix != ".py" or source.stat().st_size > 256 * 1024:
        raise error("invalid_extension", "Extension source must be a bounded Python artifact.")
    body = source.read_bytes()
    if hashlib.sha256(body).hexdigest() != args.get("implementation_sha256"):
        raise error("extension_digest_mismatch", "The snapshotted implementation changed; no code was executed.")
    tree = ast.parse(body.decode("utf-8"), filename=args["source_path"])
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            value = node.value
            if Path(value).is_absolute() or PureWindowsPath(value).drive or PureWindowsPath(value).root:
                raise error("absolute_path_literal", "Extension string literals must not contain absolute filesystem paths. Use context.path().")
    namespace = {"__name__": "cst_local_api_" + args["candidate_id"], "__file__": str(source)}
    context = ExtensionContext(controller, entry, args, runtime.contained, runtime.relative_name)
    # Authorized Python can access the entire process. An effect declaration is
    # not an access-control boundary, so any exception after this point is uncertain.
    controller.effect_started = True
    controller.context = {"api_id": args["api_id"], "candidate_id": args["candidate_id"],
                          "implementation_sha256": args["implementation_sha256"]}
    if args["effect"] != "read":
        entry["dirty_by_controller"] = True
    try:
        exec(compile(tree, args["source_path"], "exec"), namespace)
        run = namespace.get(args["entrypoint"])
        verify = namespace.get(args["verifier"])
        if not callable(run) or not callable(verify):
            raise ValueError("The implementation must provide separate run and verification functions.")
        value = run(context, args["parameters"])
        verification = runtime.clean(verify(context, args["parameters"], value))
        if (not isinstance(verification, dict) or verification.get("passed") is not True
                or not isinstance(verification.get("summary"), str) or not verification["summary"].strip()
                or len(verification["summary"]) > 4096
                or not isinstance(verification.get("evidence"), dict) or not verification["evidence"]):
            raise error("api_verification_failed", "The implementation's postcondition verifier did not provide a passing result with evidence.",
                        verification={"passed": False, "details": verification})
        result = runtime.clean(value)
        if len(json.dumps(result, allow_nan=False).encode("utf-8")) > 1024 * 1024:
            raise ValueError("API result exceeds 1 MiB; return paged data or a relative artifact path.")
        if len(json.dumps(verification, allow_nan=False).encode("utf-8")) > 64 * 1024:
            raise ValueError("Verification evidence exceeds 64 KiB.")
        return {"status": "api_verified", **controller.context, "actual_cst_version": actual_version,
                "verification": verification, "result": result, "physics_validated": False,
                "note": "Local postconditions passed for this invocation; this is not independent physics validation."}
    except Exception as cause:
        if getattr(cause, "code", None) == "api_verification_failed":
            raise
        raise error("api_execution_failed", str(cause),
                    verification={"passed": False, "summary": "Execution or verification raised an exception."}) from cause
