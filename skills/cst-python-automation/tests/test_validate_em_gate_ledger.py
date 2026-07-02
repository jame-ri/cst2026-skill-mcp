import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "validate_em_gate_ledger.py"


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


def pass_gate():
    return {
        "status": "pass",
        "evidence": "checked in saved CST project and model history",
        "reference_checked": [
            {
                "source_type": "official_help",
                "path_or_tool": r"D:\CST\Online Help\mergedProjects\3D\special_overview\special_overview_waveguideover.htm",
                "topic": "gate-specific CST help topic",
                "finding": "reference reviewed before this gate was marked pass",
            }
        ],
        "pass_condition": "required evidence is present and consistent",
        "unchecked_risk": "none for this static gate",
    }


def base_ledger():
    ledger = {
        "schema_version": 1,
        "design_intent": {
            "antenna_class": "rectangular_patch",
            "simulation_allowed": False,
            "feed_type": "microstrip",
        },
        "port_decision": {
            "feed_type": "microstrip",
            "selected_port_object": "waveguide_port",
            "signal_conductor": "patch_antenna:feed_line",
            "reference_conductor": "patch_antenna:ground",
            "dielectric_region": "patch_antenna:substrate",
            "intended_excitation": "distributed",
            "physical_port_section": "transverse_line_cross_section",
            "reference_checked": [
                {
                    "source_type": "official_help",
                    "path_or_tool": r"D:\CST\Online Help\mergedProjects\3D\special_overview\special_overview_waveguideover.htm",
                    "topic": "Waveguide Port Overview / Microstrip Lines",
                    "finding": "port object, section, and dimensions are derived from the help topic",
                }
            ],
            "port_span_includes": [
                "signal_conductor",
                "dielectric_region",
                "reference_ground",
            ],
            "dimension_basis": {
                "source_path": r"D:\CST\Online Help\mergedProjects\3D\special_overview\special_overview_waveguideover.htm",
                "source_topic": "Microstrip Lines / Port Modes / Port Dimensions",
                "chosen_rule": "use the CST Help extension-factor method for the declared feed",
                "chosen_parameters": {
                    "k": 5.0,
                    "bottom_extension": "substrate_height_to_ground",
                    "top_and_side_extension": "k_times_substrate_height",
                },
            },
            "span_parameters": {
                "zrange": ["z_ground_max", "z_port_air_max"],
            },
            "mode_line": {
                "from": "signal_conductor",
                "to": "reference_ground",
            },
        },
        "gate_ledger": {step: pass_gate() for step in REQUIRED_STEPS},
    }
    ledger["gate_ledger"]["solver_mesh_monitors"]["unchecked_risk"] = (
        "no solver run; no port-mode solve; no S-parameter/farfield/gain/efficiency conclusion"
    )
    ledger["gate_ledger"]["save_and_simulation_state"]["unchecked_risk"] = (
        "project saved for review; no solver run; no port-mode solve; no S-parameter results"
    )
    return ledger


def run_validator(data):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as handle:
        json.dump(data, handle)
        path = Path(handle.name)
    try:
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(path)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    finally:
        path.unlink(missing_ok=True)


def run_validator_file(path):
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(path)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


class GateLedgerValidatorTests(unittest.TestCase):
    def test_valid_microstrip_ledger_passes(self):
        result = run_validator(base_ledger())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS", result.stdout)

    def test_rejects_passed_gate_without_checked_reference(self):
        data = base_ledger()
        del data["gate_ledger"]["port"]["reference_checked"]

        result = run_validator(data)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("reference_checked", result.stdout)
        self.assertIn("port", result.stdout)

    def test_rejects_microstrip_port_without_help_driven_dimension_basis(self):
        data = base_ledger()
        del data["port_decision"]["dimension_basis"]

        result = run_validator(data)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("dimension_basis", result.stdout)

    def test_rejects_microstrip_port_that_only_covers_trace_face(self):
        data = base_ledger()
        data["port_decision"]["physical_port_section"] = "metal_trace_end_face"
        data["port_decision"]["port_span_includes"] = ["signal_conductor"]

        result = run_validator(data)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("microstrip", result.stdout)
        self.assertIn("transverse", result.stdout)
        self.assertIn("reference_ground", result.stdout)

    def test_rejects_not_executed_gate_in_completion_mode(self):
        data = base_ledger()
        data["gate_ledger"]["history"]["status"] = "not_executed"

        result = run_validator(data)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("history", result.stdout)
        self.assertIn("not_executed", result.stdout)

    def test_requires_manual_evidence_for_unknown_feed_profile(self):
        data = base_ledger()
        data["design_intent"]["antenna_class"] = "custom_conformal_array"
        data["design_intent"]["feed_type"] = "custom_balanced_feed"
        data["port_decision"] = {
            "feed_type": "custom_balanced_feed",
            "selected_port_object": "custom",
            "manual_review_required": True,
            "reference_checked": [
                {
                    "source_type": "user_source_document",
                    "path_or_tool": "user supplied feed drawing",
                    "topic": "custom balanced feed topology",
                    "finding": "no built-in validator profile; manual engineering evidence is required",
                }
            ],
        }

        result = run_validator(data)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("manual_evidence", result.stdout)

        data["port_decision"]["manual_evidence"] = "Reviewed against supplied feed drawing and CST screenshots."
        result = run_validator(data)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_microstrip_example_file_passes(self):
        example = SKILL_ROOT / "references" / "em-gate-ledger-microstrip-example.json"
        result = run_validator_file(example)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
