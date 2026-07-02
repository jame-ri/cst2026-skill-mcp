#!/usr/bin/env python3
"""Validate a CST electromagnetic design gate ledger.

The validator checks evidence discipline and feed-profile consistency. It does
not claim that an antenna design is electromagnetically correct.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_STEPS = [
    "requirements",
    "physical_structure",
    "parameterization",
    "materials",
    "geometry_connectivity",
    "port",
    "boundary_background",
    "solver_mesh_monitors",
    "history",
    "save_and_simulation_state",
    "delivery",
]

ALLOWED_STATUSES = {"pass", "not_applicable", "blocked", "not_executed"}

MICROSTRIP_FEEDS = {"microstrip", "cpw", "stripline", "grounded_coplanar"}
WAVEGUIDE_PORT_NAMES = {"waveguide_port", "port", "cst_port", "with_port"}
LUMPED_PORT_NAMES = {"discrete_port", "discretefaceport", "discrete_face_port"}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("ledger root must be a JSON object")
    return data


def text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def normalized(value: Any) -> str:
    return text(value).lower().replace(" ", "_").replace("-", "_")


def list_values(value: Any) -> set[str]:
    if isinstance(value, list):
        return {normalized(item) for item in value}
    if isinstance(value, str):
        return {normalized(value)}
    return set()


def has_text(value: Any) -> bool:
    return bool(text(value))


def add_missing(errors: list[str], location: str, fields: list[str], obj: dict[str, Any]) -> None:
    for field in fields:
        if not has_text(obj.get(field)):
            errors.append(f"{location}: missing `{field}`")


def validate_gate_ledger(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    gate_ledger = data.get("gate_ledger")
    if not isinstance(gate_ledger, dict):
        return ["root: missing object `gate_ledger`"]

    for step in REQUIRED_STEPS:
        entry = gate_ledger.get(step)
        if not isinstance(entry, dict):
            errors.append(f"gate_ledger.{step}: missing gate entry")
            continue

        status = normalized(entry.get("status"))
        if status not in ALLOWED_STATUSES:
            errors.append(
                f"gate_ledger.{step}: status must be one of "
                f"{sorted(ALLOWED_STATUSES)}, got `{entry.get('status')}`"
            )
        elif status in {"blocked", "not_executed"}:
            errors.append(f"gate_ledger.{step}: status `{status}` is not allowed for completion validation")

        for field in ["evidence", "pass_condition", "unchecked_risk"]:
            if field not in entry:
                errors.append(f"gate_ledger.{step}: missing `{field}`")

        if status == "pass":
            add_missing(errors, f"gate_ledger.{step}", ["evidence", "pass_condition"], entry)

    return errors


def validate_no_simulation_state(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    design_intent = data.get("design_intent", {})
    if not isinstance(design_intent, dict):
        errors.append("design_intent: must be an object")
        return errors

    if design_intent.get("simulation_allowed") is False:
        gate_ledger = data.get("gate_ledger", {})
        solver_risk = text(gate_ledger.get("solver_mesh_monitors", {}).get("unchecked_risk")).lower()
        save_risk = text(gate_ledger.get("save_and_simulation_state", {}).get("unchecked_risk")).lower()
        combined = f"{solver_risk} {save_risk}"
        for phrase in ["no solver", "no port-mode", "no s-parameter"]:
            if phrase not in combined:
                errors.append(
                    "no-simulation workflow: unchecked_risk must explicitly mention "
                    f"`{phrase}`"
                )
    return errors


def validate_microstrip_port(port: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    add_missing(
        errors,
        "port_decision",
        [
            "selected_port_object",
            "signal_conductor",
            "reference_conductor",
            "dielectric_region",
            "intended_excitation",
            "physical_port_section",
        ],
        port,
    )

    if normalized(port.get("selected_port_object")) not in WAVEGUIDE_PORT_NAMES:
        errors.append("microstrip port: selected_port_object must be `waveguide_port`")

    if normalized(port.get("intended_excitation")) != "distributed":
        errors.append("microstrip port: intended_excitation must be `distributed`")

    if "transverse" not in normalized(port.get("physical_port_section")):
        errors.append("microstrip port: physical_port_section must be a transverse line cross-section")

    required_span = {
        "signal_conductor",
        "dielectric_region",
        "reference_ground",
        "air_region",
    }
    actual_span = list_values(port.get("port_span_includes"))
    missing_span = sorted(required_span - actual_span)
    if missing_span:
        errors.append(
            "microstrip port: port_span_includes must include "
            f"{', '.join(missing_span)}"
        )

    mode_line = port.get("mode_line")
    if not isinstance(mode_line, dict):
        errors.append("microstrip port: missing `mode_line` object")
    else:
        if normalized(mode_line.get("from")) != "signal_conductor":
            errors.append("microstrip port: mode_line.from must be `signal_conductor`")
        if normalized(mode_line.get("to")) != "reference_ground":
            errors.append("microstrip port: mode_line.to must be `reference_ground`")

    return errors


def validate_lumped_port(port: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if normalized(port.get("selected_port_object")) not in LUMPED_PORT_NAMES:
        errors.append("lumped feed: selected_port_object must be `discrete_port` or `discrete_face_port`")
    if normalized(port.get("intended_excitation")) != "lumped":
        errors.append("lumped feed: intended_excitation must be `lumped`")
    terminals = port.get("terminals")
    if not isinstance(terminals, list) or len(terminals) != 2:
        errors.append("lumped feed: terminals must list exactly two physical terminals")
    return errors


def validate_coax_port(port: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if normalized(port.get("selected_port_object")) not in WAVEGUIDE_PORT_NAMES:
        errors.append("coax port: selected_port_object must be `waveguide_port`")
    required_span = {"inner_conductor", "dielectric_region", "shield_or_reference_ground"}
    missing_span = sorted(required_span - list_values(port.get("port_span_includes")))
    if missing_span:
        errors.append("coax port: port_span_includes must include " + ", ".join(missing_span))
    add_missing(errors, "coax port", ["inner_conductor", "dielectric_region", "shield_conductor"], port)
    return errors


def validate_floquet_or_plane_wave(port: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    selected = normalized(port.get("selected_port_object"))
    if selected not in {"floquet_port", "plane_wave"}:
        errors.append("periodic or incident-wave excitation: selected_port_object must be `floquet_port` or `plane_wave`")
    if port.get("periodic_boundary_declared") is not True:
        errors.append("periodic or incident-wave excitation: periodic_boundary_declared must be true")
    return errors


def validate_unknown_profile(port: dict[str, Any]) -> list[str]:
    if port.get("manual_review_required") is not True:
        return ["unknown feed profile: set manual_review_required=true or add a validator profile"]
    if not has_text(port.get("manual_evidence")):
        return ["unknown feed profile: manual_evidence is required when manual_review_required=true"]
    return []


def validate_port_decision(data: dict[str, Any]) -> list[str]:
    port = data.get("port_decision")
    if not isinstance(port, dict):
        return ["root: missing object `port_decision`"]

    feed_type = normalized(port.get("feed_type") or data.get("design_intent", {}).get("feed_type"))
    if not feed_type:
        return ["port_decision: missing `feed_type`"]

    if feed_type in MICROSTRIP_FEEDS:
        return validate_microstrip_port(port)
    if feed_type in {"probe_lumped", "lumped_gap", "two_terminal_lumped"}:
        return validate_lumped_port(port)
    if feed_type in {"coax", "coaxial"}:
        return validate_coax_port(port)
    if feed_type in {"floquet", "periodic", "plane_wave"}:
        return validate_floquet_or_plane_wave(port)
    return validate_unknown_profile(port)


def validate(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(data.get("design_intent"), dict):
        errors.append("root: missing object `design_intent`")
    errors.extend(validate_gate_ledger(data))
    errors.extend(validate_no_simulation_state(data))
    errors.extend(validate_port_decision(data))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger", type=Path, help="Path to an EM gate ledger JSON file")
    args = parser.parse_args(argv)

    try:
        data = load_json(args.ledger)
    except Exception as exc:
        print(f"FAIL: cannot read ledger: {exc}")
        return 2

    errors = validate(data)
    if errors:
        print("FAIL: electromagnetic gate ledger did not pass")
        for error in errors:
            print(f"- {error}")
        return 1

    print("PASS: electromagnetic gate ledger passed static consistency checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
