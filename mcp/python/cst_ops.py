"""CST Python helper operations used by the cst2026 MCP server.

This file is intentionally small and conservative. It standardizes common
smoke-test actions while keeping the default save policy as "no_save".
"""

from __future__ import annotations

import argparse
import ctypes
import csv
import json
import os
import math
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]


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


def _project_filename(project: Any) -> str | None:
    for name in ("filename", "get_filename", "GetFilename"):
        method = getattr(project, name, None)
        if callable(method):
            try:
                value = str(method()).strip()
                return value or None
            except Exception:
                pass
    return None


def _looks_unsaved_project(filename: str | None) -> bool:
    if not filename:
        return True
    stem = Path(filename).stem.lower()
    return stem.startswith("untitled")


def _finish_project(
    project: Any,
    *,
    save_policy: str,
    save_copy_path: str | None = None,
    include_results: bool = True,
    allow_overwrite: bool = False,
) -> dict[str, Any]:
    if save_policy not in {"no_save", "save_copy", "save_original"}:
        raise RuntimeError(f"Invalid save_policy: {save_policy}")

    before_filename = _project_filename(project)
    actions: list[str] = []
    saved_path: str | None = None

    if save_policy == "save_copy":
        if not save_copy_path:
            raise RuntimeError("save_copy requires --save-copy-path.")
        saved_path = _path(save_copy_path)
        if Path(saved_path).suffix.lower() != ".cst":
            raise RuntimeError("save_copy_path must end with .cst.")
        Path(saved_path).parent.mkdir(parents=True, exist_ok=True)
        save = getattr(project, "save", None)
        if not callable(save):
            raise RuntimeError("Project.save is unavailable.")
        save(saved_path, include_results, allow_overwrite)
        actions.append("project.save(save_copy_path)")
    elif save_policy == "save_original":
        if _looks_unsaved_project(before_filename):
            raise RuntimeError("save_original cannot be used for an unsaved/Untitled project; use save_copy instead.")
        save = getattr(project, "save", None)
        if not callable(save):
            raise RuntimeError("Project.save is unavailable.")
        save("", include_results, allow_overwrite)
        saved_path = before_filename
        actions.append("project.save(original)")
    else:
        actions.append("no_save")

    close = getattr(project, "close", None)
    if not callable(close):
        raise RuntimeError("Project.close is unavailable.")
    close()
    actions.append("project.close()")

    return {
        "save_policy": save_policy,
        "before_filename": before_filename,
        "saved_path": saved_path,
        "include_results": include_results,
        "allow_overwrite": allow_overwrite,
        "actions": actions,
    }


def _jsonable(value: Any, limit: int = 200) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, complex):
        return {"real": value.real, "imag": value.imag, "abs": abs(value)}
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "tolist"):
        try:
            return _jsonable(value.tolist(), limit=limit)
        except Exception:
            pass
    if isinstance(value, dict):
        return {str(key): _jsonable(item, limit=limit) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        seq = list(value)
        converted = [_jsonable(item, limit=limit) for item in seq[:limit]]
        if len(seq) > limit:
            converted.append({"truncated_count": len(seq) - limit})
        return converted
    return str(value)


def _value_or_call(obj: Any, name: str) -> tuple[bool, Any, str | None]:
    attr = getattr(obj, name, None)
    if attr is None:
        return False, None, None
    try:
        return True, attr() if callable(attr) else attr, None
    except Exception as exc:  # pragma: no cover - depends on CST COM behavior
        return True, None, f"{name}: {exc}"


def _first_value(obj: Any, names: list[str], *args: Any) -> tuple[Any, str | None, list[str]]:
    errors: list[str] = []
    for name in names:
        attr = getattr(obj, name, None)
        if attr is None:
            continue
        try:
            if callable(attr):
                return attr(*args), name, errors
            if args:
                errors.append(f"{name}: attribute is not callable")
                continue
            return attr, name, errors
        except Exception as exc:  # pragma: no cover - depends on CST COM behavior
            errors.append(f"{name}: {exc}")
    return None, None, errors


def _public_callables(obj: Any, limit: int = 80) -> list[str]:
    names: list[str] = []
    try:
        for name in dir(obj):
            if name.startswith("_"):
                continue
            try:
                if callable(getattr(obj, name, None)):
                    names.append(name)
            except Exception:
                continue
    except Exception:
        return []
    return sorted(names)[:limit]


def _open_for_inspection(project_path: str, require_open: bool) -> tuple[Any, Any, Any, list[str], list[str]]:
    interface = _load_interface()
    before = _running_environments(interface)
    de = _connect_existing_or_new(interface, allow_new=not require_open)
    project = _get_open_project(de, project_path, require_open=require_open)
    after = _running_environments(interface)
    return interface, de, project, before, after


def _project_summary(project: Any, project_path: str) -> dict[str, Any]:
    fields = {
        "filename": ["filename", "get_filename", "GetFilename"],
        "folder": ["folder", "get_folder", "GetFolder"],
        "project_type": ["project_type", "get_project_type", "GetProjectType"],
    }
    summary: dict[str, Any] = {
        "project_path": project_path,
        "project_object": str(project),
        "available_project_methods_sample": _public_callables(project),
    }
    warnings: list[str] = []
    for key, names in fields.items():
        value, method, errors = _first_value(project, names)
        summary[key] = _jsonable(value)
        summary[f"{key}_method"] = method
        warnings.extend(errors)
    if warnings:
        summary["warnings"] = warnings
    return summary


def _compact_messages(value: Any, limit: int = 80) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        parts = [line.strip() for line in value.splitlines() if line.strip()]
        return parts[:limit] if parts else [value[:1000]]
    if hasattr(value, "tolist"):
        try:
            value = value.tolist()
        except Exception:
            pass
    if isinstance(value, (list, tuple, set)):
        return [str(item)[:1000] for item in list(value)[:limit]]
    return [str(value)[:1000]]


def _project_messages(project: Any, limit: int = 80) -> tuple[list[str], list[str]]:
    value, method, errors = _first_value(project, ["get_messages", "GetMessages", "messages"])
    warnings = [f"messages.{item}" for item in errors]
    messages = _compact_messages(value, limit=limit)
    if method is None:
        warnings.append("Project messages API was not available.")
    return messages, warnings


def _message_warnings(messages: list[str], limit: int = 50) -> list[str]:
    keywords = (
        "warning",
        "error",
        "failed",
        "mesh",
        "port",
        "material",
        "boundary",
        "convergence",
        "license",
    )
    hits = [message for message in messages if any(keyword in message.lower() for keyword in keywords)]
    return hits[:limit]


def _model_tree(project: Any, max_items: int) -> dict[str, Any]:
    warnings: list[str] = []
    model3d = getattr(project, "model3d", None)
    if model3d is None:
        return {"items": [], "count": 0, "warnings": ["project.model3d is unavailable."]}
    method = getattr(model3d, "get_tree_items", None)
    if not callable(method):
        return {
            "items": [],
            "count": 0,
            "available_model3d_methods_sample": _public_callables(model3d),
            "warnings": ["model3d.get_tree_items is unavailable."],
        }
    try:
        items = method()
    except TypeError:
        try:
            items = method("")
        except Exception as exc:  # pragma: no cover - depends on CST COM behavior
            warnings.append(f"model3d.get_tree_items failed: {exc}")
            items = []
    except Exception as exc:  # pragma: no cover - depends on CST COM behavior
        warnings.append(f"model3d.get_tree_items failed: {exc}")
        items = []
    as_strings = [str(item) for item in list(items or [])]
    return {
        "items": as_strings[:max_items],
        "count": len(as_strings),
        "truncated": len(as_strings) > max_items,
        "available_model3d_methods_sample": _public_callables(model3d),
        "warnings": warnings,
    }


def _load_results():
    try:
        import cst.results as results  # type: ignore
    except Exception as exc:  # pragma: no cover - depends on CST install
        raise RuntimeError(
            "Failed to import cst.results. Run this helper with CST's bundled Python "
            "or set CST_PYTHON_EXE to the CST Python executable."
        ) from exc
    return results


def _get_result_tree_items(module: Any, filter_name: str, max_items: int) -> dict[str, Any]:
    method = getattr(module, "get_tree_items", None)
    if not callable(method):
        return {"items": [], "count": 0, "warnings": ["get_tree_items is unavailable."]}
    warnings: list[str] = []
    try:
        items = method(filter_name)
    except TypeError:
        try:
            items = method()
            warnings.append(f"Filter '{filter_name}' was ignored because this CST API accepted no filter argument.")
        except Exception as exc:  # pragma: no cover - depends on CST COM behavior
            warnings.append(f"get_tree_items('{filter_name}') failed: {exc}")
            items = []
    except Exception as exc:  # pragma: no cover - depends on CST COM behavior
        warnings.append(f"get_tree_items('{filter_name}') failed: {exc}")
        items = []
    as_strings = [str(item) for item in list(items or [])]
    return {
        "items": as_strings[:max_items],
        "count": len(as_strings),
        "truncated": len(as_strings) > max_items,
        "warnings": warnings,
    }


def _result_tree(project_path: str, max_items: int) -> dict[str, Any]:
    output: dict[str, Any] = {"modules": {}, "warnings": [], "errors": []}
    try:
        results = _load_results()
        project_file = results.ProjectFile(project_path, allow_interactive=True)
    except Exception as exc:
        output["errors"].append(str(exc))
        return output

    for module_name, getter_name in (("3d", "get_3d"), ("schematic", "get_schematic")):
        getter = getattr(project_file, getter_name, None)
        if not callable(getter):
            output["warnings"].append(f"ProjectFile.{getter_name} is unavailable.")
            continue
        try:
            module = getter()
        except Exception as exc:  # pragma: no cover - depends on CST COM behavior
            output["warnings"].append(f"ProjectFile.{getter_name} failed: {exc}")
            continue
        output["modules"][module_name] = {
            "0d_1d": _get_result_tree_items(module, "0D/1D", max_items),
            "colormap": _get_result_tree_items(module, "colormap", max_items),
            "available_methods_sample": _public_callables(module),
        }
    return output


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    lower = text.lower()
    return any(keyword in lower for keyword in keywords)


def _matching_items(items: list[str], keywords: tuple[str, ...], limit: int = 60) -> list[str]:
    return [item for item in items if _contains_any(item, keywords)][:limit]


def _classify_geometry_items(items: list[str]) -> dict[str, list[str]]:
    return {
        "solids_sheets_components": _matching_items(
            items,
            ("component", "solid", "sheet", "brick", "cylinder", "sphere", "cone", "extrude", "wire", "curve"),
        ),
        "likely_conductors": _matching_items(
            items,
            ("metal", "pec", "copper", "aluminium", "aluminum", "gold", "ground", "patch", "trace", "via", "pin", "shield"),
        ),
        "likely_dielectrics": _matching_items(
            items,
            ("substrate", "dielectric", "fr4", "rogers", "teflon", "vacuum", "air", "lens", "radome"),
        ),
        "feed_or_port_related": _matching_items(
            items,
            ("port", "feed", "coax", "microstrip", "stripline", "cpw", "waveguide", "floquet", "discrete", "lumped"),
        ),
        "boundary_or_region_related": _matching_items(
            items,
            ("boundary", "open", "pml", "airbox", "background", "symmetry", "periodic", "unit cell"),
        ),
        "boolean_transform_related": _matching_items(
            items,
            ("boolean", "subtract", "intersect", "unite", "merge", "transform", "mirror", "rotate", "translate", "array"),
        ),
    }


def _physics_inventory(model_items: list[str], result_tree: dict[str, Any]) -> dict[str, Any]:
    result_items: list[str] = []
    for module in result_tree.get("modules", {}).values():
        for bucket in ("0d_1d", "colormap"):
            result_items.extend(module.get(bucket, {}).get("items", []))
    all_items = model_items + result_items
    checks = {
        "materials": _matching_items(all_items, ("material", "pec", "copper", "fr4", "rogers", "dielectric", "loss", "conduct")),
        "ports_feeds": _matching_items(all_items, ("port", "feed", "mode", "floquet", "waveguide", "discrete", "lumped")),
        "boundaries_background": _matching_items(all_items, ("boundary", "background", "open", "pml", "electric", "magnetic", "periodic", "unit cell")),
        "solver_frequency": _matching_items(all_items, ("solver", "frequency", "time domain", "eigen", "integral", "s-parameter", "s parameter")),
        "mesh_adaptation": _matching_items(all_items, ("mesh", "adaptive", "tetra", "hexa", "cells", "refinement")),
        "monitors_farfield": _matching_items(all_items, ("monitor", "farfield", "far field", "field", "gain", "efficiency")),
        "result_paths": result_items[:80],
    }
    checklist: dict[str, Any] = {}
    for key, evidence in checks.items():
        checklist[key] = {
            "found_in_accessible_tree": bool(evidence),
            "evidence": evidence[:40],
        }
    return checklist


def inspect_project(args: argparse.Namespace) -> int:
    project_path = _path(args.project)
    _, de, project, before, after = _open_for_inspection(project_path, require_open=args.require_open)
    model_tree = _model_tree(project, args.max_tree_items)
    messages, message_api_warnings = _project_messages(project)
    result_tree = _result_tree(project_path, args.max_tree_items) if args.include_results else {"skipped": True}
    warnings = []
    warnings.extend(model_tree.get("warnings", []))
    warnings.extend(message_api_warnings)
    warnings.extend(result_tree.get("warnings", []))
    warnings.extend(result_tree.get("errors", []))
    message_hits = _message_warnings(messages)
    if message_hits:
        warnings.append("Project messages contain warning/error/physics keywords; inspect message_warnings.")
    _json(
        {
            "ok": True,
            "operation": "inspect-project",
            "project": _project_summary(project, project_path),
            "running_before": before,
            "running_after": after,
            "open_projects": _safe_list_open_projects(de),
            "model_tree": model_tree,
            "result_tree": result_tree,
            "messages": messages,
            "message_warnings": message_hits,
            "warnings": warnings,
            "save_policy": "no_save",
        }
    )
    return 0


def inspect_geometry(args: argparse.Namespace) -> int:
    project_path = _path(args.project)
    _, de, project, before, after = _open_for_inspection(project_path, require_open=args.require_open)
    model_tree = _model_tree(project, args.max_tree_items)
    items = model_tree.get("items", [])
    inventory = _classify_geometry_items(items)
    warnings = list(model_tree.get("warnings", []))
    if not items:
        warnings.append("No model tree items were accessible; geometry cannot be validated from this helper.")
    if not any(inventory.values()):
        warnings.append("No geometry-like evidence was classified from the accessible tree; inspect CST UI or macro history before modeling.")
    warnings.append(
        "This is a tree-derived inspection. Exact bounding boxes, contacts, and material assignments still need CST API/UI confirmation when topology matters."
    )
    _json(
        {
            "ok": True,
            "operation": "inspect-geometry",
            "project_path": project_path,
            "running_before": before,
            "running_after": after,
            "open_projects": _safe_list_open_projects(de),
            "geometry_inventory": inventory,
            "model_tree": model_tree,
            "warnings": warnings,
            "save_policy": "no_save",
        }
    )
    return 0


def inspect_physics(args: argparse.Namespace) -> int:
    project_path = _path(args.project)
    _, de, project, before, after = _open_for_inspection(project_path, require_open=args.require_open)
    model_tree = _model_tree(project, args.max_tree_items)
    result_tree = _result_tree(project_path, args.max_tree_items)
    messages, message_api_warnings = _project_messages(project)
    checklist = _physics_inventory(model_tree.get("items", []), result_tree)
    warnings = []
    warnings.extend(model_tree.get("warnings", []))
    warnings.extend(result_tree.get("warnings", []))
    warnings.extend(result_tree.get("errors", []))
    warnings.extend(message_api_warnings)
    for key, entry in checklist.items():
        if key != "result_paths" and not entry["found_in_accessible_tree"]:
            warnings.append(f"{key} was not found in accessible model/result trees; verify before solving.")
    message_hits = _message_warnings(messages)
    if message_hits:
        warnings.append("Project messages contain warning/error/physics keywords; inspect message_warnings.")
    _json(
        {
            "ok": True,
            "operation": "inspect-physics",
            "project_path": project_path,
            "running_before": before,
            "running_after": after,
            "open_projects": _safe_list_open_projects(de),
            "physics_checklist": checklist,
            "model_tree": model_tree,
            "result_tree": result_tree,
            "messages": messages,
            "message_warnings": message_hits,
            "warnings": warnings,
            "save_policy": "no_save",
        }
    )
    return 0


def _all_result_paths(result_tree: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    for module in result_tree.get("modules", {}).values():
        for bucket in ("0d_1d", "colormap"):
            paths.extend(module.get(bucket, {}).get("items", []))
    return paths


def _is_s_parameter_path(path: str) -> bool:
    lower = path.lower().replace(" ", "")
    return (
        "s-parameter" in lower
        or "sparameter" in lower
        or "\\s" in lower
        or "/s" in lower
        or "s[" in lower
        or "s1,1" in lower
        or "s2,1" in lower
    )


def _as_sequence(value: Any) -> list[Any]:
    if value is None:
        return []
    if hasattr(value, "tolist"):
        try:
            value = value.tolist()
        except Exception:
            pass
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def _as_float(value: Any) -> float | None:
    try:
        if isinstance(value, complex):
            return float(value.real)
        return float(value)
    except Exception:
        return None


def _magnitude(value: Any) -> float | None:
    try:
        if isinstance(value, complex):
            mag = abs(value)
        elif isinstance(value, (list, tuple)) and value:
            mag = _magnitude(value[-1])
        else:
            mag = abs(float(value))
        if mag is None or not math.isfinite(float(mag)):
            return None
        return float(mag)
    except Exception:
        return None


def _result_item_summary(module: Any, tree_path: str, run_id: int, target_frequency: float | None) -> dict[str, Any]:
    get_item = getattr(module, "get_result_item", None)
    if not callable(get_item):
        return {"tree_path": tree_path, "errors": ["get_result_item is unavailable on this result module."]}
    errors: list[str] = []
    try:
        item = get_item(tree_path, run_id=run_id, load_impedances=True)
    except TypeError:
        try:
            item = get_item(tree_path, run_id)
        except Exception as exc:  # pragma: no cover - depends on CST COM behavior
            return {"tree_path": tree_path, "errors": [f"get_result_item failed: {exc}"]}
    except Exception as exc:  # pragma: no cover - depends on CST COM behavior
        return {"tree_path": tree_path, "errors": [f"get_result_item failed: {exc}"]}

    metadata: dict[str, Any] = {"tree_path": tree_path}
    for name in ("title", "treepath", "xlabel", "ylabel", "length"):
        exists, value, error = _value_or_call(item, name)
        if exists:
            metadata[name] = _jsonable(value)
        if error:
            errors.append(error)

    xdata, _, x_errors = _first_value(item, ["get_xdata", "GetXData"])
    ydata, _, y_errors = _first_value(item, ["get_ydata", "GetYData"])
    data, _, data_errors = _first_value(item, ["get_data", "GetData"])
    ref_impedance, _, ref_errors = _first_value(item, ["get_ref_imp_data", "GetRefImpData"])
    errors.extend(x_errors + y_errors + data_errors + ref_errors)

    xs = _as_sequence(xdata)
    ys = _as_sequence(ydata)
    raw_data = _as_sequence(data)
    values = ys
    if not values and raw_data:
        values = [point[-1] if isinstance(point, (list, tuple)) and point else point for point in raw_data]
    magnitudes = [mag for mag in (_magnitude(value) for value in values) if mag is not None]
    summary: dict[str, Any] = {
        **metadata,
        "point_count": max(len(xs), len(values), len(raw_data)),
        "x_sample": _jsonable(xs[:5]),
        "y_sample": _jsonable(values[:5]),
        "data_sample": _jsonable(raw_data[:5]),
        "ref_impedance_sample": _jsonable(_as_sequence(ref_impedance)[:5]),
        "errors": errors,
    }
    if magnitudes:
        summary["min_magnitude"] = min(magnitudes)
        summary["max_magnitude"] = max(magnitudes)
    if target_frequency is not None and xs and values:
        indexed = [
            (idx, abs(freq - target_frequency))
            for idx, freq in enumerate((_as_float(item) for item in xs))
            if freq is not None and idx < len(values)
        ]
        if indexed:
            nearest_idx = min(indexed, key=lambda pair: pair[1])[0]
            summary["target_frequency"] = target_frequency
            summary["nearest_x_value"] = _jsonable(xs[nearest_idx])
            summary["nearest_y_value"] = _jsonable(values[nearest_idx])
            summary["nearest_magnitude"] = _magnitude(values[nearest_idx])
    return summary


def result_sanity(args: argparse.Namespace) -> int:
    project_path = _path(args.project)
    max_items = args.max_tree_items
    result_tree = _result_tree(project_path, max_items)
    all_paths = _all_result_paths(result_tree)
    selected_paths = [args.tree_path] if args.tree_path else [path for path in all_paths if _is_s_parameter_path(path)][:8]
    warnings = []
    errors = list(result_tree.get("errors", []))
    warnings.extend(result_tree.get("warnings", []))
    if not all_paths:
        warnings.append("No result-tree paths were discovered; saved results may be missing or inaccessible.")
    if not selected_paths:
        warnings.append("No S-parameter-like result path was auto-selected. Provide --tree-path for a specific result.")

    summaries: list[dict[str, Any]] = []
    if selected_paths:
        try:
            results = _load_results()
            project_file = results.ProjectFile(project_path, allow_interactive=True)
            modules = []
            for getter_name in ("get_3d", "get_schematic"):
                getter = getattr(project_file, getter_name, None)
                if callable(getter):
                    try:
                        modules.append(getter())
                    except Exception as exc:  # pragma: no cover - depends on CST COM behavior
                        warnings.append(f"ProjectFile.{getter_name} failed while reading results: {exc}")
            for tree_path in selected_paths:
                item_summary = None
                for module in modules:
                    item_summary = _result_item_summary(module, tree_path, args.run_id, args.target_frequency)
                    if not item_summary.get("errors"):
                        break
                if item_summary is None:
                    item_summary = {"tree_path": tree_path, "errors": ["No result module was available."]}
                summaries.append(item_summary)
        except Exception as exc:
            errors.append(str(exc))

    sanity_checks = {
        "result_tree_available": bool(all_paths),
        "selected_paths": selected_paths,
        "passive_sparameter_magnitude_lte_1": None,
    }
    max_mag = None
    for summary in summaries:
        if "max_magnitude" not in summary:
            continue
        max_mag = summary["max_magnitude"] if max_mag is None else max(max_mag, summary["max_magnitude"])
    if args.passive and max_mag is not None:
        sanity_checks["passive_sparameter_magnitude_lte_1"] = max_mag <= 1.0001
        if max_mag > 1.0001:
            warnings.append(
                f"Passive S-parameter sanity check failed: max |S|={max_mag:.6g} is greater than 1. "
                "Check active devices, renormalization, ports, calibration planes, or result interpretation."
            )

    _json(
        {
            "ok": not errors,
            "operation": "result-sanity",
            "project_path": project_path,
            "result_tree": result_tree,
            "result_summaries": summaries,
            "sanity_checks": sanity_checks,
            "warnings": warnings,
            "errors": errors,
            "save_policy": "no_save",
        }
    )
    return 0 if not errors else 1


def _bytes_to_gb(value: int | float | None) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value) / (1024**3), 3)
    except Exception:
        return None


def _system_memory() -> dict[str, Any]:
    if os.name != "nt":
        return {"available": False, "reason": "Windows GlobalMemoryStatusEx is not available on this OS."}

    class MemoryStatusEx(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    status = MemoryStatusEx()
    status.dwLength = ctypes.sizeof(MemoryStatusEx)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):  # type: ignore[attr-defined]
        return {"available": False, "reason": "GlobalMemoryStatusEx failed."}
    return {
        "available": True,
        "memory_load_percent": int(status.dwMemoryLoad),
        "total_physical_gb": _bytes_to_gb(status.ullTotalPhys),
        "available_physical_gb": _bytes_to_gb(status.ullAvailPhys),
        "total_pagefile_gb": _bytes_to_gb(status.ullTotalPageFile),
        "available_pagefile_gb": _bytes_to_gb(status.ullAvailPageFile),
    }


def _disk_status(path_value: str | None) -> dict[str, Any]:
    path = Path(path_value or REPO_ROOT)
    if path.is_file():
        path = path.parent
    if not path.exists():
        path = REPO_ROOT
    usage = shutil.disk_usage(path)
    return {
        "path": str(path),
        "total_gb": _bytes_to_gb(usage.total),
        "used_gb": _bytes_to_gb(usage.used),
        "free_gb": _bytes_to_gb(usage.free),
    }


def _cst_install_dir() -> Path | None:
    for key in ("CST_INSTALL_DIR", "CST_HOME", "CST_ROOT"):
        value = os.environ.get(key)
        if value and Path(value).exists():
            return Path(value)
    exe = Path(sys.executable)
    if exe.name.lower() == "python.exe" and exe.parent.name.lower() == "python":
        root = exe.parent.parent
        if (root / "Patches").exists():
            return root
    for candidate in (Path("D:/CST"), Path("C:/CST")):
        if candidate.exists():
            return candidate
    return None


def _update_manager_status() -> dict[str, Any]:
    install_dir = _cst_install_dir()
    if install_dir is None:
        return {"available": False, "warnings": ["CST install directory was not found for Update Manager log inspection."]}
    log_path = install_dir / "Patches" / "log.txt"
    result_path = install_dir / "Patches" / "Result"
    warnings: list[str] = []
    recent_log = ""
    result_text = ""
    for path, label in ((log_path, "log"), (result_path, "result")):
        try:
            if path.exists():
                text = path.read_text(encoding="utf-8", errors="replace")
                if label == "log":
                    recent_log = text[-12000:]
                else:
                    result_text = text[-2000:]
        except Exception as exc:
            warnings.append(f"Could not read CST Update Manager {label} file {path}: {exc}")

    combined = f"{recent_log}\n{result_text}"
    license_error = "license details are required to check for updates" in combined.lower()
    if license_error:
        warnings.append(
            "CST Update Manager reports missing license details for update checks. "
            "This can create a startup dialog; disable automatic software updates in CST Preferences "
            "or repair CST Update Manager/license settings."
        )

    return {
        "available": log_path.exists() or result_path.exists(),
        "install_dir": str(install_dir),
        "log_path": str(log_path),
        "result_path": str(result_path),
        "license_update_check_error": license_error,
        "warnings": warnings,
    }


def _run_json_powershell(script: str) -> Any:
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "PowerShell command failed.")
    text = completed.stdout.strip()
    if not text:
        return []
    return json.loads(text)


def _tasklist_processes() -> list[dict[str, Any]]:
    completed = subprocess.run(
        ["tasklist", "/fo", "csv", "/nh"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "tasklist failed.")
    rows = csv.reader(completed.stdout.splitlines())
    processes: list[dict[str, Any]] = []
    for row in rows:
        if len(row) < 5:
            continue
        mem_kb = None
        try:
            mem_kb = int(row[4].replace(",", "").replace(" K", "").replace("KB", "").strip())
        except Exception:
            pass
        processes.append(
            {
                "pid": int(row[1]),
                "name": row[0],
                "command_line": None,
                "working_set_gb": _bytes_to_gb((mem_kb or 0) * 1024),
                "source": "tasklist",
            }
        )
    return processes


def _windows_processes() -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    script = r"""
$items = Get-CimInstance Win32_Process | Select-Object ProcessId,Name,CommandLine,WorkingSetSize,CreationDate
$items | ConvertTo-Json -Depth 3
"""
    try:
        raw = _run_json_powershell(script)
        if isinstance(raw, dict):
            raw = [raw]
        processes = []
        for item in raw or []:
            processes.append(
                {
                    "pid": item.get("ProcessId"),
                    "name": item.get("Name"),
                    "command_line": item.get("CommandLine"),
                    "working_set_gb": _bytes_to_gb(item.get("WorkingSetSize")),
                    "creation_date": item.get("CreationDate"),
                    "source": "Get-CimInstance",
                }
            )
        return processes, warnings
    except Exception as exc:
        warnings.append(f"Get-CimInstance process query failed, falling back to tasklist: {exc}")
        try:
            return _tasklist_processes(), warnings
        except Exception as fallback_exc:
            warnings.append(f"tasklist process query failed: {fallback_exc}")
            return [], warnings


def _matches_process(process: dict[str, Any], patterns: list[str]) -> bool:
    text = f"{process.get('name') or ''} {process.get('command_line') or ''}".lower()
    return any(pattern.lower() in text for pattern in patterns)


def _process_snapshot(patterns: list[str], include_commandline: bool) -> dict[str, Any]:
    processes, warnings = _windows_processes()
    matched = [item for item in processes if _matches_process(item, patterns)]
    normalized: list[dict[str, Any]] = []
    for item in matched:
        row = {
            "pid": item.get("pid"),
            "name": item.get("name"),
            "working_set_gb": item.get("working_set_gb"),
            "creation_date": item.get("creation_date"),
            "source": item.get("source"),
        }
        if include_commandline:
            row["command_line"] = item.get("command_line")
        normalized.append(row)
    total_gb = round(sum(float(item.get("working_set_gb") or 0) for item in normalized), 3)
    return {
        "patterns": patterns,
        "count": len(normalized),
        "total_working_set_gb": total_gb,
        "processes": sorted(normalized, key=lambda item: float(item.get("working_set_gb") or 0), reverse=True),
        "warnings": warnings,
    }


def _process_snapshot_for_pids(pids: list[int], include_commandline: bool) -> dict[str, Any]:
    processes, warnings = _windows_processes()
    wanted = set(pids)
    matched = [item for item in processes if item.get("pid") in wanted]
    normalized: list[dict[str, Any]] = []
    for item in matched:
        row = {
            "pid": item.get("pid"),
            "name": item.get("name"),
            "working_set_gb": item.get("working_set_gb"),
            "creation_date": item.get("creation_date"),
            "source": item.get("source"),
        }
        if include_commandline:
            row["command_line"] = item.get("command_line")
        normalized.append(row)
    return {
        "pids": pids,
        "count": len(normalized),
        "total_working_set_gb": round(sum(float(item.get("working_set_gb") or 0) for item in normalized), 3),
        "processes": normalized,
        "missing_pids": [pid for pid in pids if pid not in {item.get("pid") for item in normalized}],
        "warnings": warnings,
    }


def _default_process_patterns(raw_patterns: list[str] | None = None) -> list[str]:
    if raw_patterns:
        return [item for item in raw_patterns if item]
    return [
        "cst design environment",
        "cst design environment_amd64.exe",
        "modeler_amd64.exe",
        "schematic_amd64.exe",
        "schematiceditor_amd64.exe",
        "dbstorageserver_amd64.exe",
        "cstdc",
        "cstd.exe",
        "solverserver_amd64.exe",
    ]


def process_status(args: argparse.Namespace) -> int:
    patterns = _default_process_patterns(args.pattern or None)
    disk_path = args.work_dir or args.project or str(REPO_ROOT)
    update_manager = _update_manager_status()
    snapshot = {
        "ok": True,
        "operation": "process-status",
        "process_snapshot": _process_snapshot(patterns, include_commandline=args.include_commandline),
        "system_memory": _system_memory(),
        "disk": _disk_status(disk_path),
        "update_manager": update_manager,
        "warnings": update_manager.get("warnings", []),
        "save_policy": "no_save",
    }
    _json(snapshot)
    return 0


def preflight_resources(args: argparse.Namespace) -> int:
    patterns = _default_process_patterns(args.pattern or None)
    process_info = _process_snapshot(patterns, include_commandline=args.include_commandline)
    memory = _system_memory()
    disk = _disk_status(args.work_dir or args.project or str(REPO_ROOT))
    update_manager = _update_manager_status()
    warnings: list[str] = []
    blockers: list[str] = []
    recommendations: list[str] = []
    warnings.extend(update_manager.get("warnings", []))

    process_count = int(process_info.get("count") or 0)
    if process_count > args.max_cst_processes:
        blockers.append(f"Matched CST-related process count {process_count} exceeds limit {args.max_cst_processes}.")
        recommendations.append("Reuse one open CST session or stop explicitly selected stale PIDs before starting another solve.")

    for item in process_info.get("processes", []):
        mem = float(item.get("working_set_gb") or 0)
        if mem > args.max_single_cst_memory_gb:
            warnings.append(
                f"Process PID {item.get('pid')} uses {mem:.3f} GB, above per-process warning threshold "
                f"{args.max_single_cst_memory_gb:.3f} GB."
            )

    free_mem = memory.get("available_physical_gb") if memory.get("available") else None
    if free_mem is not None and float(free_mem) < args.min_free_memory_gb:
        blockers.append(f"Available physical memory {free_mem:.3f} GB is below required {args.min_free_memory_gb:.3f} GB.")
        recommendations.append("Pause the batch, reduce mesh/monitor load, or close explicitly selected CST processes before solving.")
    if free_mem is None:
        warnings.append("Available physical memory could not be measured.")

    free_disk = disk.get("free_gb")
    if free_disk is not None and float(free_disk) < args.min_free_disk_gb:
        blockers.append(f"Free disk space {free_disk:.3f} GB is below required {args.min_free_disk_gb:.3f} GB.")
        recommendations.append("Move job outputs or clean solver artifacts before starting a long CST task.")

    project_path = Path(args.project).resolve() if args.project else None
    if project_path and not project_path.exists():
        warnings.append(f"Project path does not exist yet: {project_path}")

    ok = len(blockers) == 0
    _json(
        {
            "ok": ok,
            "operation": "preflight-resources",
            "project_path": str(project_path) if project_path else None,
            "process_snapshot": process_info,
            "system_memory": memory,
            "disk": disk,
            "update_manager": update_manager,
            "thresholds": {
                "min_free_memory_gb": args.min_free_memory_gb,
                "min_free_disk_gb": args.min_free_disk_gb,
                "max_cst_processes": args.max_cst_processes,
                "max_single_cst_memory_gb": args.max_single_cst_memory_gb,
            },
            "blockers": blockers,
            "warnings": warnings,
            "recommendations": recommendations,
            "save_policy": "no_save",
        }
    )
    return 0 if ok else 2


def cleanup_stale_processes(args: argparse.Namespace) -> int:
    pids = [int(pid) for pid in args.pid]
    if not args.allow_terminate:
        raise RuntimeError("Refusing to terminate processes without --allow-terminate.")
    if not pids:
        raise RuntimeError("No PIDs were provided. This helper never kills processes by name.")

    before = _process_snapshot_for_pids(pids, include_commandline=True)
    results: list[dict[str, Any]] = []
    for pid in pids:
        command = ["taskkill", "/PID", str(pid), "/T"]
        if args.force:
            command.append("/F")
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        results.append(
            {
                "pid": pid,
                "command": command,
                "exit_code": completed.returncode,
                "stdout": completed.stdout.strip(),
                "stderr": completed.stderr.strip(),
            }
        )
    time.sleep(1)
    after = _process_snapshot_for_pids(pids, include_commandline=True)
    ok = all(item["exit_code"] == 0 for item in results)
    _json(
        {
            "ok": ok,
            "operation": "cleanup-stale-processes",
            "pids": pids,
            "force": bool(args.force),
            "before": before,
            "results": results,
            "after": after,
            "warnings": [
                "This helper only terminates explicitly provided PIDs. Verify they belong to the stalled CST job before using force."
            ],
            "save_policy": "no_save",
        }
    )
    return 0 if ok else 1


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


def close_project(args: argparse.Namespace) -> int:
    interface = _load_interface()
    project_path = _path(args.project)
    before = _running_environments(interface)
    de = _connect_existing_or_new(interface, allow_new=not args.require_open)
    project = _get_open_project(de, project_path, require_open=args.require_open)
    close_result = _finish_project(
        project,
        save_policy=args.save_policy,
        save_copy_path=args.save_copy_path,
        include_results=args.include_results,
        allow_overwrite=args.allow_overwrite,
    )
    de_closed = False
    if args.close_design_environment:
        de.close()
        de_closed = True
    after = _running_environments(interface)
    _json(
        {
            "ok": True,
            "operation": "close-project",
            "project_path": project_path,
            "running_before": before,
            "running_after": after,
            "open_projects": [] if de_closed else _safe_list_open_projects(de),
            "closed_design_environment": de_closed,
            **close_result,
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

    close = sub.add_parser("close-project")
    close.add_argument("--project", required=True)
    close.add_argument("--save-policy", choices=["no_save", "save_copy", "save_original"], default="no_save")
    close.add_argument("--save-copy-path")
    close.add_argument("--include-results", action="store_true")
    close.add_argument("--allow-overwrite", action="store_true")
    close.add_argument("--require-open", action="store_true")
    close.add_argument("--close-design-environment", action="store_true")

    live = sub.add_parser("live-modify")
    live.add_argument("--project", required=True)
    live.add_argument("--parameter", required=True)
    live.add_argument("--test-value", required=True)
    live.add_argument("--pause-after-set", type=float, default=5)
    live.add_argument("--restore", action="store_true")
    live.add_argument("--require-open", action="store_true")

    inspect = sub.add_parser("inspect-project")
    inspect.add_argument("--project", required=True)
    inspect.add_argument("--require-open", action="store_true")
    inspect.add_argument("--max-tree-items", type=int, default=300)
    inspect.add_argument("--include-results", action="store_true")

    geometry = sub.add_parser("inspect-geometry")
    geometry.add_argument("--project", required=True)
    geometry.add_argument("--require-open", action="store_true")
    geometry.add_argument("--max-tree-items", type=int, default=500)

    physics = sub.add_parser("inspect-physics")
    physics.add_argument("--project", required=True)
    physics.add_argument("--require-open", action="store_true")
    physics.add_argument("--max-tree-items", type=int, default=500)

    sanity = sub.add_parser("result-sanity")
    sanity.add_argument("--project", required=True)
    sanity.add_argument("--tree-path")
    sanity.add_argument("--run-id", type=int, default=0)
    sanity.add_argument("--max-tree-items", type=int, default=500)
    sanity.add_argument("--target-frequency", type=float)
    sanity.add_argument("--passive", action="store_true")

    status = sub.add_parser("process-status")
    status.add_argument("--project")
    status.add_argument("--work-dir")
    status.add_argument("--pattern", action="append")
    status.add_argument("--include-commandline", action="store_true")

    preflight = sub.add_parser("preflight-resources")
    preflight.add_argument("--project")
    preflight.add_argument("--work-dir")
    preflight.add_argument("--pattern", action="append")
    preflight.add_argument("--include-commandline", action="store_true")
    preflight.add_argument("--min-free-memory-gb", type=float, default=8.0)
    preflight.add_argument("--min-free-disk-gb", type=float, default=10.0)
    preflight.add_argument("--max-cst-processes", type=int, default=2)
    preflight.add_argument("--max-single-cst-memory-gb", type=float, default=48.0)

    cleanup = sub.add_parser("cleanup-stale-processes")
    cleanup.add_argument("--pid", action="append", type=int, required=True)
    cleanup.add_argument("--allow-terminate", action="store_true")
    cleanup.add_argument("--force", action="store_true")

    args = parser.parse_args()
    try:
        if args.command == "closed-start":
            return closed_start(args)
        if args.command == "close-project":
            return close_project(args)
        if args.command == "live-modify":
            return live_modify(args)
        if args.command == "inspect-project":
            return inspect_project(args)
        if args.command == "inspect-geometry":
            return inspect_geometry(args)
        if args.command == "inspect-physics":
            return inspect_physics(args)
        if args.command == "result-sanity":
            return result_sanity(args)
        if args.command == "process-status":
            return process_status(args)
        if args.command == "preflight-resources":
            return preflight_resources(args)
        if args.command == "cleanup-stale-processes":
            return cleanup_stale_processes(args)
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

