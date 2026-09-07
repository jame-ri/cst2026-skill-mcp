"""Regression checks for CST gate evidence and task scope. No CST required."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills" / "cst-python-automation"
spec = importlib.util.spec_from_file_location("cst_gate_validator", SKILL / "scripts" / "validate_em_gate_ledger.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class GateLedgerTests(unittest.TestCase):
    def setUp(self):
        self.ledger = json.loads((SKILL / "references" / "em-gate-ledger-microstrip-example.json").read_text(encoding="utf8"))

    def test_example_passes_and_blank_template_fails(self):
        self.assertEqual(gate.validate(self.ledger), [])
        template = json.loads((SKILL / "references" / "em-gate-ledger-template.json").read_text(encoding="utf8"))
        self.assertTrue(gate.validate(template))

    def test_empty_containers_and_booleans_are_not_evidence(self):
        for value in [[], {}, False, True, 0, "  ", None]:
            with self.subTest(value=value):
                ledger = copy.deepcopy(self.ledger)
                ledger["gate_ledger"]["geometry_connectivity"]["evidence"] = value
                self.assertTrue(gate.validate(ledger))

    def test_not_applicable_requires_a_reason(self):
        entry = self.ledger["gate_ledger"]["materials"]
        entry.update(status="not_applicable", evidence="", pass_condition="")
        self.assertTrue(gate.validate(self.ledger))

    def test_status_is_not_an_error_class(self):
        self.ledger["gate_ledger"]["port"]["status"] = "port_setup_error"
        self.assertTrue(gate.validate(self.ledger))

    def test_missing_or_malformed_reference_is_rejected(self):
        refs = self.ledger["port_decision"]["reference_checked"]
        refs.append("not a reference object")
        self.assertTrue(gate.validate(self.ledger))
        self.ledger["port_decision"]["reference_checked"] = [{
            "source_type": "official_help", "path_or_tool": "docs.read_official_doc",
            "topic": "Port", "finding": {}
        }]
        self.assertTrue(gate.validate(self.ledger))

    def test_structured_no_simulation_state_is_language_independent(self):
        self.ledger["simulation_state"] = {
            "solver_executed": False, "port_modes_executed": False, "results_validated": False
        }
        for step in ["solver_mesh_monitors", "save_and_simulation_state"]:
            self.ledger["gate_ledger"][step]["unchecked_risk"] = "Results remain unchecked."
        self.assertEqual(gate.validate(self.ledger), [])

    def test_legacy_no_simulation_caveats_remain_supported(self):
        self.ledger.pop("simulation_state", None)
        self.assertEqual(gate.validate(self.ledger), [])

    def test_no_simulation_cannot_claim_execution(self):
        for field in ["solver_executed", "port_modes_executed", "results_validated"]:
            ledger = copy.deepcopy(self.ledger)
            ledger["simulation_state"] = {
                "solver_executed": False, "port_modes_executed": False, "results_validated": False
            }
            ledger["simulation_state"][field] = True
            self.assertTrue(gate.validate(ledger))

    def test_simulation_flags_require_boolean_types(self):
        self.ledger["design_intent"]["simulation_allowed"] = "false"
        self.assertTrue(gate.validate(self.ledger))
        self.ledger["design_intent"]["simulation_allowed"] = False
        for state in [{}, [], {"solver_executed": "false"}]:
            self.ledger["simulation_state"] = state
            self.assertTrue(gate.validate(self.ledger))

    def test_malformed_nested_objects_return_errors_instead_of_crashing(self):
        for field in ["gate_ledger", "design_intent", "port_decision"]:
            for value in [None, [], "invalid", 3]:
                ledger = copy.deepcopy(self.ledger)
                ledger[field] = value
                self.assertTrue(gate.validate(ledger))
        for value in [None, [], 3]:
            ledger = copy.deepcopy(self.ledger)
            ledger["gate_ledger"]["solver_mesh_monitors"] = value
            self.assertTrue(gate.validate(ledger))
        self.assertTrue(gate.validate([]))

    def test_declared_feed_cannot_conflict_with_port_profile(self):
        self.ledger["design_intent"]["feed_type"] = "coax"
        self.assertTrue(gate.validate(self.ledger))

    def plane_wave(self):
        self.ledger["design_intent"]["feed_type"] = "plane_wave"
        self.ledger["port_decision"] = {
            "feed_type": "plane_wave", "selected_port_object": "plane_wave",
            "propagation_direction": "+z", "polarization": "linear x",
            "boundary_basis": "Open-boundary excitation for the declared scattering problem",
            "periodic_boundary_declared": False,
            "reference_checked": [{
                "source_type": "cst_official_doc",
                "path_or_tool": "official-docs/vba-3d/special_vbaports/special_vbaports_planewave_object.htm",
                "topic": "PlaneWave object",
                "finding": "Open-boundary excitation; periodic imprint is a separate option"
            }]
        }
        return self.ledger

    def test_open_boundary_plane_wave_is_not_forced_to_be_periodic(self):
        self.assertEqual(gate.validate(self.plane_wave()), [])

    def test_plane_wave_requires_boundary_and_excitation_evidence(self):
        self.plane_wave()
        self.ledger["port_decision"]["boundary_basis"] = ""
        self.assertTrue(gate.validate(self.ledger))

    def test_periodic_profile_still_requires_periodic_declaration(self):
        self.plane_wave()
        self.ledger["design_intent"]["feed_type"] = "periodic"
        self.ledger["port_decision"]["feed_type"] = "periodic"
        self.assertTrue(gate.validate(self.ledger))
        self.ledger["port_decision"]["periodic_boundary_declared"] = True
        self.assertEqual(gate.validate(self.ledger), [])

    def test_lumped_terminals_must_be_nonempty_and_distinct(self):
        self.plane_wave()
        self.ledger["design_intent"]["feed_type"] = "lumped_gap"
        port = self.ledger["port_decision"]
        port.update(feed_type="lumped_gap", selected_port_object="discrete_port", intended_excitation="lumped")
        for terminals in [[], ["", ""], [None, None], ["signal", "signal"]]:
            port["terminals"] = terminals
            self.assertTrue(gate.validate(self.ledger))
        port["terminals"] = ["signal endpoint", "reference endpoint"]
        self.assertEqual(gate.validate(self.ledger), [])


if __name__ == "__main__":
    unittest.main()
