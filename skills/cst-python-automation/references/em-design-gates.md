# Electromagnetic Design Gates

Use this reference for nontrivial CST model creation, mutation, repair, or solver setup. The purpose is to stop CST automation from treating object creation as electromagnetic validation.

## Mandatory Ledger

Before editing or solving, open a gate ledger. Each applicable step must be reported with exactly these fields:

| field | requirement |
| --- | --- |
| `step` | One of the gate steps below |
| `status` | Exactly `pass`, `not_applicable`, `blocked`, or `not_executed` |
| `evidence` | CST state, History caption, project tree, geometry inventory, official help, installed macro, design record, or explicit user input |
| `pass_condition` | What must be true for this step to pass |
| `unchecked_risk` | What remains unverified, especially when no solver or port-mode solve was run |

Never use vague statuses such as `looks ok`, `probably`, `assumed`, or `created`. If evidence is missing, the status is not `pass`.

## Gate Steps

1. `requirements`
   - Confirm task type, project source, output expectation, save policy, automation mode, frequency band, and whether simulation is allowed.
   - For review-gated tasks, default to no solver run until the user confirms.

2. `physical_structure`
   - Record the electromagnetic problem, intended observable, coordinate system, propagation/radiation directions, layer stack, materials, conductor roles, feed topology, and boundary meaning.
   - Stop when a missing detail changes topology, connectivity, excitation, boundary condition, or result interpretation.

3. `parameterization`
   - Units and CST parameters must exist before History commands reference them.
   - User-tunable dimensions and reused derived coordinates must be CST parameters, not opaque helper-side numbers.

4. `materials`
   - Verify every dielectric, conductor, lossy material, PEC, finite-conductivity metal, and background material against the structure brief.
   - Unknown material values must remain explicit assumptions.

5. `geometry_connectivity`
   - Verify expected objects, bounding boxes, layer heights, conductor thickness, gaps, slots, Boolean results, and contact/isolation intent.
   - Signal conductors that should touch must physically contact or overlap. Conductors that should be isolated must have nonzero intended clearance.
   - Ground or shield conductors required by the feed must be present and continuous.

6. `port`
   - Classify feed type, signal conductor, reference conductor or shield, dielectric region, physical port section or lumped terminals, intended mode, and distributed-vs-lumped excitation before creating the port.
   - Choose the CST port object from feed physics, not convenience.
   - Tree presence of `Ports\portN`, a History `Port` command, or a picked face is only object-existence evidence. It is not physical validation.

7. `boundary_background`
   - Verify airbox/background and boundary conditions match antenna, waveguide, periodic, symmetry, or closed-cavity physics.
   - Port planes and boundaries must not cut through active geometry unless that cut is the intended physical cross-section.

8. `solver_mesh_monitors`
   - Verify solver type, frequency range, S-parameter normalization, monitors, mesh strategy, and refinements match the requested metrics.
   - For no-simulation tasks, mark unsolved mesh/adaptive convergence as unchecked risk and do not report performance metrics.

9. `history`
   - Verify visible History captions for units, parameters, materials, each physical object, Boolean/pick operations, ports, boundaries, mesh, monitors, and solver setup.
   - A successful helper script is not enough; check persisted `Model/3D/ModelHistory.json` or an equivalent CST inspection tool.

10. `save_and_simulation_state`
   - Verify save path, save policy, project copy/version, close policy, and whether any solver result tree exists.
   - If the user requested no simulation, explicitly report `no solver run`, `no port-mode solve`, and `no S-parameter/farfield/gain/efficiency conclusion`.

11. `delivery`
   - Provide project path, design id or version, gate ledger, port decision record, History evidence, assumptions, unchecked risks, and next allowed action.

## Microstrip And Grounded-Line Port Gate

For microstrip, CPW, stripline, and grounded coplanar feeds:

- Preferred CST object: waveguide `Port` on the feed line's transverse cross-section for distributed-line excitation.
- Required physical coverage: signal conductor, dielectric region, all relevant reference grounds, and needed air region.
- Required reference: mode line or calibration line from signal conductor to reference ground.
- Required orientation: propagation into the modeled feed line, consistent with the selected transverse section.
- Not sufficient: port object exists; port is attached to calculation-domain boundary; only the metal trace end face was picked; the reference ground is outside the port span; mode line is missing or not signal-to-ground.
- Stop condition: if the transverse section cannot be created, selected, or verified, mark `port` as `blocked` or `port_setup_error`; do not present the CST project as complete.

Use `DiscretePort` or `DiscreteFacePort` only when the intended excitation is a short lumped approximation, and record that approximation explicitly.

## Evidence Hierarchy

Prefer evidence in this order:

1. Explicit user requirement or source document.
2. Official CST Help or installed macro pattern for the exact command class.
3. Saved CST project inspection: tree, object inventory, material list, port list, physics setup, result tree, message log.
4. Persisted History captions and commands.
5. Helper script calculations and manifest.

Evidence from levels 4-5 alone must not be used to claim electromagnetic correctness when levels 2-3 are available and relevant.

## Stop Rules

Stop and report a blocker instead of continuing when:

- The feed topology or reference conductor is unknown.
- A distributed feed was replaced with a lumped port for convenience.
- The port section does not include the needed signal, dielectric, reference ground, and air/field region.
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
- Classify the feed before creating the port.
- For microstrip, require a waveguide `Port` on the full transverse section.
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
