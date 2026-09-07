# Electromagnetic design gates

Use for nontrivial model creation, mutation, repair or solver setup. Pure reference
questions and read-only extraction do not require a full model ledger. For partial
work, report checked and unchecked scope honestly; a full completion validator may
correctly reject a partial ledger.

## Evidence and ledger contract

Each gate entry is keyed by its step name and contains:

| Field | Contract |
| --- | --- |
| status | pass, not_applicable, blocked, or not_executed |
| evidence | Nonempty text describing the observed state or justified non-applicability |
| reference_checked | Source entries with source_type, path_or_tool, topic and finding |
| pass_condition | Nonempty text defining the criterion or why it does not apply |
| unchecked_risk | Text describing remaining limitations; may be empty when none |

Error categories such as port_setup_error are diagnoses, not gate statuses.
Never mark an unchecked required property pass or use not_applicable to bypass it.

A reference establishes the rule or API being used; project/History/result evidence
establishes what actually happened. An official Help page is not evidence that a
particular project's contacts or ports are correct. Record both where necessary.

Check the source before an unfamiliar or changed decision. A previously checked,
version-compatible source may be reused for unchanged operations; record it again
by reference rather than repeatedly loading the same documentation.

## Checks by stage

| Step | Required check |
| --- | --- |
| requirements | Target, objective, outputs, save policy, material assumptions and simulation scope |
| physical_structure | Coordinates, units, band, topology/layers, conductor roles, return path and excitation |
| parameterization | Units and parameter definitions precede dependent History; editable values remain expressions |
| materials | Intended regions, properties, units, losses/background and explicit unknowns |
| geometry_connectivity | Object/dimension evidence, Boolean results, actual contacts, intended gaps and ground continuity |
| port | Source-backed excitation model, physical section or terminals, reference, orientation and calibration |
| boundary_background | Boundaries/background match radiation, waveguide, symmetry, periodic or cavity intent |
| solver_mesh_monitors | Solver, band, requested observables, monitors, mesh intent and relevant normalization |
| history | Readable, persisted entries for the modeled objects and settings, using supported inspection |
| save_and_simulation_state | Actual saved/copy identity, save/close policy and observed execution/result state |
| delivery | Requested deliverables, verified scope, artifacts, assumptions and remaining risks |

An explicit solve request can authorize the scoped run after prerequisites pass.
Keep an explicitly requested review gate. Modeling-only requests leave the solver
unexecuted; passing static setup checks does not imply convergence or performance.

Recheck dependent gates after model, parameter, port, boundary or solver changes.
Tree presence and successful History submission alone do not prove physical contact,
modal correctness, save success or numerical convergence.

## Port decision and validator profiles

Choose from the declared excitation and checked sources, not an antenna name or
API convenience. Record the physical section/terminals, signal/reference/dielectric
roles where applicable, mode or incident-wave definition, and reference_checked.

For distributed feeds record dimension_basis: source_path, source_topic, chosen_rule,
and the selected parameters. Do not silently replace a modal feed with a lumped
approximation. Any approximation needs an explicit physical basis and task scope.

| feed_type | Static profile |
| --- | --- |
| microstrip, cpw, stripline, grounded_coplanar | Distributed waveguide Port; transverse section, signal/dielectric/ground span, dimension basis and signal-to-ground mode line |
| coax, coaxial | Waveguide Port; inner conductor, dielectric and shield aperture coverage |
| probe_lumped, lumped_gap, two_terminal_lumped | Explicit lumped approximation; discrete/face discrete port and two nonempty terminal descriptions |
| floquet, periodic | Floquet or supported periodic plane-wave excitation with declared periodic boundaries |
| plane_wave | PlaneWave source, propagation/polarization and boundary_basis; periodic boundaries are not universally required |
| other | manual_review_required with substantive manual_evidence and source, or a new implemented profile |

Plane-wave profile basis: the repository's
[PlaneWave object documentation](../../../official-docs/vba-3d/special_vbaports/special_vbaports_planewave_object.htm)
describes open-boundary excitation and a separate optional periodic imprint setting.
Check the solver-specific boundary and monitor requirements for the actual task.

If geometry inspection cannot establish a required contact, or the chosen excitation
contradicts its source, mark the affected gate blocked. Report the artifact as
partial/requiring review; do not claim the model passed. Preserve unrelated progress.

## Simulation state and validation

Use [the template](em-gate-ledger-template.json) and
[the review-only example](em-gate-ledger-microstrip-example.json). Example findings
are illustrative, never evidence for a new project.

For simulation_allowed: false, record simulation_state with solver_executed,
port_modes_executed and results_validated all false. Explain in ordinary language
that numerical performance and convergence remain unchecked. Legacy ledgers without
this object still require the existing explicit no-simulation caveat phrases.

Run from the repository root, using an available Python interpreter:

~~~sh
python skills/cst-python-automation/scripts/validate_em_gate_ledger.py design-records/run/gate-ledger.json
~~~

The validator checks field consistency and declared profiles. It does not open CST,
validate physical geometry, rerun a solver, verify arbitrary source claims, or prove
antenna performance. A blocked/not_executed required gate prevents full completion.

A valid review-only delivery can say the model was saved and static checks passed,
while explicitly stating that no solver/port-mode solve ran and no performance
conclusions were established. A requested simulation is incomplete until its actual
execution and requested results have been checked.
