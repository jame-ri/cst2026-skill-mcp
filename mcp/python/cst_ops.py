"""CST Python helper operations used by the cst2026 MCP server.

This file is intentionally small and conservative. It standardizes common
smoke-test actions while keeping the default save policy as "no_save".
"""

from __future__ import annotations

import argparse
import json
import os
import time
import traceback
from pathlib import Path
from typing import Any


def _json(data: dict[str, Any]) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _path(value: str) -> str:
    return str(Path(value).resolve())


def _load_interface():
    try:
        import cst.interface as interface  # type: ignore
    except Exception as exc:  # pragma: no cover - depends on CST install
        raise RuntimeError(
            "Failed to import cst.interface. Run this helper with CST's bundled Python "
            "or set CST_PYTHON_EXE to the CST Python executable."
        ) from exc
    return interface


def _call_if_exists(obj: Any, names: list[str], *args: Any) -> Any:
    errors: list[str] = []
    for name in names:
        method = getattr(obj, name, None)
        if callable(method):
            try:
                return method(*args)
            except Exception as exc:  # pragma: no cover - depends on CST COM behavior
                errors.append(f"{name}: {exc}")
    if errors:
        raise RuntimeError("; ".join(errors))
    raise AttributeError(f"None of these methods exist: {', '.join(names)}")


def _safe_list_open_projects(de: Any) -> list[str]:
    for name in ("list_open_projects", "get_open_projects"):
        method = getattr(de, name, None)
        if callable(method):
            try:
                result = method()
                return [str(item) for item in result]
            except Exception:
                pass
    return []


def _connect_existing_or_new(interface: Any, allow_new: bool) -> Any:
    design_environment = interface.DesignEnvironment
    connect_existing = getattr(design_environment, "connect_to_any", None)
    if callable(connect_existing):
        try:
            return connect_existing()
        except Exception:
            if not allow_new:
                raise
    connect_any_or_new = getattr(design_environment, "connect_to_any_or_new", None)
    if callable(connect_any_or_new):
        return connect_any_or_new()
    new = getattr(design_environment, "new", None)
    if callable(new):
        try:
            return new(options=["-i"])
        except TypeError:
            return new()
    raise RuntimeError("Could not connect to or start a CST DesignEnvironment.")


def _running_environments(interface: Any) -> list[str]:
    running = getattr(interface.DesignEnvironment, "running_design_environments", None)
    if callable(running):
        try:
            return [str(item) for item in running()]
        except Exception:
            return []
    return []


def _open_project(de: Any, project_path: str) -> Any:
    open_project = getattr(de, "open_project", None)
    if not callable(open_project):
        raise RuntimeError("DesignEnvironment.open_project is unavailable.")
    return open_project(project_path)


def _same_path(left: str, right: str) -> bool:
    try:
        return os.path.normcase(os.path.abspath(left)) == os.path.normcase(os.path.abspath(right))
    except Exception:
        return left.lower() == right.lower()


def _get_open_project(de: Any, project_path: str, require_open: bool) -> Any:
    open_projects = _safe_list_open_projects(de)
    matched = [item for item in open_projects if _same_path(item, project_path)]
    if matched:
        getter = getattr(de, "get_open_project", None)
        if callable(getter):
            try:
                return getter(matched[0])
            except Exception:
                return getter(project_path)
    if require_open:
        raise RuntimeError(
            f"Target project is not open in CST: {project_path}. "
            f"Open projects: {open_projects}"
        )
    return _open_project(de, project_path)


def _get_parameter(project: Any, name: str) -> Any:
    for obj in (getattr(project, "schematic", None), project):
        if obj is None:
            continue
        for method_name in ("GetParameter", "get_parameter", "RestoreParameterExpression"):
            method = getattr(obj, method_name, None)
            if callable(method):
                try:
                    return method(name)
                except Exception:
                    pass
    return None


def _store_parameter(project: Any, name: str, value: Any) -> str:
    errors: list[str] = []
    for label, obj in (("schematic", getattr(project, "schematic", None)), ("project", project)):
        if obj is None:
            continue
        method = getattr(obj, "StoreParameter", None)
        if callable(method):
            try:
                method(name, value)
                return f"{label}.StoreParameter"
            except Exception as exc:
                errors.append(f"{label}.StoreParameter: {exc}")
    raise RuntimeError("Failed to store parameter. " + "; ".join(errors))


def _rebuild(project: Any) -> str:
    targets = [
        ("model3d.full_history_rebuild", getattr(getattr(project, "model3d", None), "full_history_rebuild", None), ()),
        ("model3d.Rebuild", getattr(getattr(project, "model3d", None), "Rebuild", None), ()),
        (
            "model3d.RebuildOnParametricChange",
            getattr(getattr(project, "model3d", None), "RebuildOnParametricChange", None),
            (True, False),
        ),
        ("project.Rebuild", getattr(project, "Rebuild", None), ()),
        ("project.RebuildOnParametricChange", getattr(project, "RebuildOnParametricChange", None), (True, False)),
    ]
    errors: list[str] = []
    for label, method, args in targets:
        if callable(method):
            try:
                method(*args)
                return label
            except Exception as exc:
                errors.append(f"{label}: {exc}")
    raise RuntimeError("Failed to rebuild. " + "; ".join(errors))


def closed_start(args: argparse.Namespace) -> int:
    interface = _load_interface()
    project_path = _path(args.project)
    before = _running_environments(interface)
    de = _connect_existing_or_new(interface, allow_new=True)
    project = _open_project(de, project_path)
    after = _running_environments(interface)
    _json(
        {
            "ok": True,
            "operation": "closed-start",
            "project_path": project_path,
            "running_before": before,
            "running_after": after,
            "open_projects": _safe_list_open_projects(de),
            "project_object": str(project),
            "save_policy": "no_save",
        }
    )
    return 0


def live_modify(args: argparse.Namespace) -> int:
    interface = _load_interface()
    project_path = _path(args.project)
    de = _connect_existing_or_new(interface, allow_new=False)
    project = _get_open_project(de, project_path, require_open=args.require_open)
    original_value = _get_parameter(project, args.parameter)
    set_method = _store_parameter(project, args.parameter, args.test_value)
    rebuild_method = _rebuild(project)
    if args.pause_after_set > 0:
        time.sleep(args.pause_after_set)

    restore_method = None
    restore_rebuild_method = None
    if args.restore:
        if original_value is None:
            raise RuntimeError(f"Cannot restore parameter {args.parameter}; original value could not be read.")
        restore_method = _store_parameter(project, args.parameter, original_value)
        restore_rebuild_method = _rebuild(project)

    _json(
        {
            "ok": True,
            "operation": "live-modify",
            "project_path": project_path,
            "parameter": args.parameter,
            "original_value": original_value,
            "test_value": args.test_value,
            "set_method": set_method,
            "rebuild_method": rebuild_method,
            "restore": bool(args.restore),
            "restore_method": restore_method,
            "restore_rebuild_method": restore_rebuild_method,
            "open_projects": _safe_list_open_projects(de),
            "save_policy": "no_save",
        }
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="CST helper operations for cst2026 MCP.")
    sub = parser.add_subparsers(dest="command", required=True)

    closed = sub.add_parser("closed-start")
    closed.add_argument("--project", required=True)

    live = sub.add_parser("live-modify")
    live.add_argument("--project", required=True)
    live.add_argument("--parameter", required=True)
    live.add_argument("--test-value", required=True)
    live.add_argument("--pause-after-set", type=float, default=5)
    live.add_argument("--restore", action="store_true")
    live.add_argument("--require-open", action="store_true")

    args = parser.parse_args()
    try:
        if args.command == "closed-start":
            return closed_start(args)
        if args.command == "live-modify":
            return live_modify(args)
    except Exception as exc:
        _json(
            {
                "ok": False,
                "operation": args.command,
                "error": str(exc),
                "traceback": traceback.format_exc(),
                "save_policy": "no_save",
            }
        )
        return 1
    raise RuntimeError(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())

