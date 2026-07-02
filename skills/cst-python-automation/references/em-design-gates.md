# Electromagnetic Design Gates

Use this reference for nontrivial CST model creation, mutation, repair, or solver setup. The purpose is to stop CST automation from treating object creation as electromagnetic validation.

## Mandatory Ledger

Before editing or solving, open a gate ledger. Each applicable step must be reported with exactly these fields:

| field | requirement |
| --- | --- |
| `step` | One of the gate steps below |
| `status` | Exactly `pass`, `not_applicable`, `blocked`, or `not_executed` |
| `evidence` | CST state, History caption, project tree, geometry inventory, official help, installed macro, design record, or explicit user input |
| `reference_checked` | The Help/doc/macro/source file checked before executing this step: `source_type`, `path_or_tool`, `topic`, and `finding` |
| `pass_condition` | What must be true for this step to pass |
| `unchecked_risk` | What remains unverified, especially when no solver or port-mode solve was run |

Never use vague statuses such as `looks ok`, `probably`, `assumed`, or `created`. If evidence is missing, the status is not `pass`.

## Help-First Gate Discipline

Every gate is evidence-led. Before executing or marking a gate, first check a source that matches that gate:

| Gate | Check before acting |
| --- | --- |
| `requirements` | User request, supplied paper/drawing, or project brief; record exact constraints before modeling. |
| `physical_structure` | CST Help, an installed example macro, or supplied source describing the topology/feed class. |
| `parameterization` | Units, parameters, and expression syntax in CST Help or existing repository recipes. |
| `materials` | Material/background Help or a trusted macro/source for the material definitions used. |
| `geometry_connectivity` | CST solid/Boolean/pick Help or macro pattern for the geometry operations used. |
| `port` | The CST Help page or installed macro for the exact feed/port type and its dimension/setup rules. |
| `boundary_background` | Boundary/background/open-region Help for the declared electromagnetic problem. |
| `solver_mesh_monitors` | Solver, mesh, monitor, port-mode, and result-path Help for the requested metrics. |
| `history` | CST Python/VBA/History documentation or macro pattern for persisted, visible History entries. |
| `save_and_simulation_state` | CST project save/open/close and result-tree API documentation. |
| `delivery` | This gate document and the task request, so completion language matches solved vs review-only state. |

Do not fill gaps from memory when CST Help, official docs, installed macros, or a supplied source can answer the step. The gate passes only when `reference_checked` records the file/tool, topic, and finding used before the action.

Use `references/em-gate-ledger-template.json` as a fillable starting point. It intentionally contains `not_executed` statuses and should fail completion validation until replaced with task evidence.

Use `references/em-gate-ledger-microstrip-example.json` as a valid no-simulation microstrip example.

Before claiming that a generated or modified CST model is ready for review or simulation, run:

```bash
python skills/cst-python-automation/scripts/validate_em_gate_ledger.py path/to/gate-ledger.json
```

The validator checks universal gate completeness, no-simulation caveats, and feed-profile consistency. It does not prove antenna performance or replace CST simulation, port-mode solve, field/current review, or human engineering judgment.

## Gate Steps

1. `requirements`
   - First check the user request and any supplied source file; record the exact task boundary before building anything.
   - Confirm task type, project source, output expectation, save policy, automation mode, frequency band, and whether simulation is allowed.
   - For review-gated tasks, default to no solver run until the user confirms.

2. `physical_structure`
   - First check a relevant CST Help topic, installed macro, supplied drawing, or paper for the declared topology/feed class.
   - Record the electromagnetic problem, intended observable, coordinate system, propagation/radiation directions, layer stack, materials, conductor roles, feed topology, and boundary meaning.
   - Stop when a missing detail changes topology, connectivity, excitation, boundary condition, or result interpretation.

3. `parameterization`
   - First check CST units/parameter/expression documentation or an existing recipe for the parameter commands being used.
   - Units and CST parameters must exist before History commands reference them.
   - User-tunable dimensions and reused derived coordinates must be CST parameters, not opaque helper-side numbers.

4. `materials`
   - First check CST material/background documentation or a trusted macro/source for each material class used.
   - Verify every dielectric, conductor, lossy material, PEC, finite-conductivity metal, and background material against the structure brief.
   - Unknown material values must remain explicit assumptions.

5. `geometry_connectivity`
   - First check CST solid, pick, Boolean, transform, and coordinate-system documentation or macro patterns for the geometry operations.
   - Verify expected objects, bounding boxes, layer heights, conductor thickness, gaps, slots, Boolean results, and contact/isolation intent.
   - Signal conductors that should touch must physically contact or overlap. Conductors that should be isolated must have nonzero intended clearance.
   - Ground or shield conductors required by the feed must be present and continuous.

6. `port`
   - First check CST Help or an installed macro for the exact feed/port type before choosing the port object or dimensions.
   - Classify feed type, signal conductor, reference conductor or shield, dielectric region, physical port section or lumped terminals, intended mode, and distributed-vs-lumped excitation before creating the port.
   - Choose the CST port object from feed physics, not convenience.
   - Tree presence of `Ports\portN`, a History `Port` command, or a picked face is only object-existence evidence. It is not physical validation.

7. `boundary_background`
   - First check boundary/background/open-region Help for the declared antenna, waveguide, periodic, symmetry, or cavity problem.
   - Verify airbox/background and boundary conditions match antenna, waveguide, periodic, symmetry, or closed-cavity physics.
   - Port planes and boundaries must not cut through active geometry unless that cut is the intended physical cross-section.

8. `solver_mesh_monitors`
   - First check solver, mesh, monitor, port-mode, and requested-result Help for the metrics being prepared or read.
   - Verify solver type, frequency range, S-parameter normalization, monitors, mesh strategy, and refinements match the requested metrics.
   - For no-simulation tasks, mark unsolved mesh/adaptive convergence as unchecked risk and do not report performance metrics.

9. `history`
   - First check CST History/add_to_history documentation or an installed macro pattern for the commands being persisted.
   - Verify visible History captions for units, parameters, materials, each physical object, Boolean/pick operations, ports, boundaries, mesh, monitors, and solver setup.
   - A successful helper script is not enough; check persisted `Model/3D/ModelHistory.json` or an equivalent CST inspection tool.

10. `save_and_simulation_state`
   - First check CST project save/open/close and result-tree documentation before claiming save or solve state.
   - Verify save path, save policy, project copy/version, close policy, and whether any solver result tree exists.
   - If the user requested no simulation, explicitly report `no solver run`, `no port-mode solve`, and `no S-parameter/farfield/gain/efficiency conclusion`.

11. `delivery`
   - First check this gate document and the current request before writing completion language.
   - Provide project path, design id or version, gate ledger, port decision record, History evidence, assumptions, unchecked risks, and next allowed action.

## Reference-Guided Port Gate

The port gate teaches a process, not memorized dimensions. For any feed:

- Locate and read the CST Help page, official doc, installed macro, or supplied source for the exact feed type before defining the port.
- Record `reference_checked` in both the `port` gate and `port_decision`.
- Record a `dimension_basis` for distributed ports: source path/tool, topic, chosen rule, chosen parameters, and any verification or unchecked risk.
- Select the CST port object from the checked source and the feed physics. Do not silently replace a distributed modal feed with a lumped port.
- Verify the physical section or terminals, signal/reference conductors, dielectric/field region, propagation orientation, and mode/calibration definition against the checked source.
- Not sufficient: port object exists; port appears in the tree; a History command succeeded; a port is placed on a calculation boundary without proving it is the feed section; dimensions are copied from memory.
- Stop condition: if the relevant Help/source cannot be found, or the source contradicts the planned port, mark `port` as `blocked` or `port_setup_error`; do not present the CST project as complete.

Use `DiscretePort` or `DiscreteFacePort` only when the intended excitation is a short lumped approximation, and record that approximation explicitly.

## Validator Profiles

The validator does not infer physics from an antenna name. It reads the declared `feed_type` and `port_decision` from the ledger, then applies the matching profile:

| `feed_type` | What is checked |
| --- | --- |
| `microstrip`, `cpw`, `stripline`, `grounded_coplanar` | Distributed waveguide `Port`, transverse line section, signal/dielectric/reference-ground span, source-backed `dimension_basis`, and signal-to-ground mode/calibration record |
| `coax`, `coaxial` | Waveguide `Port`, inner conductor, dielectric, shield/reference conductor, and aperture coverage |
| `probe_lumped`, `lumped_gap`, `two_terminal_lumped` | Discrete or face discrete port, lumped excitation declaration, and exactly two terminals |
| `floquet`, `periodic`, `plane_wave` | Floquet port or plane wave declaration and periodic-boundary declaration |
| any other value | `manual_review_required: true` plus nonempty `manual_evidence`, or a new validator profile |

This keeps the gate usable for different antennas: the script checks whether declared electromagnetic intent and evidence are complete and internally consistent. It does not guess topology from names such as patch, Yagi, Vivaldi, array, or metasurface.

## Evidence Hierarchy

Prefer evidence in this order:

1. Explicit user requirement or source document.
2. Official CST Help or installed macro pattern for the exact gate topic and command class.
3. Saved CST project inspection: tree, object inventory, material list, port list, physics setup, result tree, message log.
4. Persisted History captions and commands.
5. Helper script calculations and manifest.

Evidence from levels 4-5 alone must not be used to claim electromagnetic correctness when levels 2-3 are available and relevant.

## Stop Rules

Stop and report a blocker instead of continuing when:

- The feed topology or reference conductor is unknown.
- A distributed feed was replaced with a lumped port for convenience.
- The port section, dimensions, or terminals are not supported by the checked Help/source for the declared feed.
- Geometry inspection cannot confirm required contact/isolation or ground continuity.
- Boundary conditions were chosen from a default template without a physical reason.
- A no-simulation workflow is being used but the response starts to imply S-parameters, gain, efficiency, or tuning success.
- History entries are missing, hidden, or too collapsed for user inspection.

## Known Baseline Failure To Prevent

Pressure scenario:

```text
User asks for a 1.65 GHz rectangular microstrip patch antenna in CST, no simulation, review only.
Agent builds geometry and creates a CST waveguide Port.
Agent checks that the port appears in the tree and History, then says the model is complete.
User asks whether the port was validated.
The real issue: the agent did not run the port gate. The port object existed, but the physical transverse microstrip section, reference ground coverage, dielectric span, orientation, and mode line were not proven.
```

Required behavior with this skill:

- Open the gate ledger before modeling.
- For each gate, check the relevant Help/doc/macro/source first and record it in `reference_checked`.
- Classify the feed before creating the port.
- For microstrip, read the CST Waveguide Port / Microstrip Help before selecting the port section and dimensions; record the Help-driven `dimension_basis`.
- Record the evidence and unchecked risk for no-simulation review.
- If only object existence was checked, mark the port gate as not passed and do not call the project complete.

## Completion Language

Allowed:

```text
The model is saved for review. Static gates passed for requirements, structure, parameters, materials, geometry/connectivity, port object selection, boundary setup, History persistence, and save state. No solver or port-mode solve was run, so S-parameters, gain, efficiency, convergence, and modal field quality are unchecked.
```

Not allowed:

```text
The antenna is complete and should work.
```

Not allowed when the port gate is incomplete:

```text
The port is fine because it appears under Ports and the History command succeeded.
```
