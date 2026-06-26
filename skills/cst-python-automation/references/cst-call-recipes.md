# CST Call Recipes

Use this file before rediscovering CST calls from scratch. Each recipe gives the
default sequence, the MCP tools to prefer, and the CST History/API pattern to
confirm when MCP coverage is not enough.

## project-management

Purpose: open, inspect, version, checkpoint, and close CST projects without
modal dialogs or accidental saves.

Default sequence:

1. Run `cst.process_status` or `cst.preflight_resources` before starting CST or
   a long job.
2. Use `cst.closed_start` only when an existing open session/project is not
   already suitable.
3. Inspect with `cst.inspect_project` before modifying a project.
4. Create a design or job record with `records.create_variant` or
   `cst.job_checkpoint` for multi-stage work.
5. For helper-owned projects, finish with `cst.close_project` using one explicit
   policy: `no_save`, `save_copy`, or `save_original`.

Rules:

- Do not call `DesignEnvironment.close()` while a helper-owned unsaved project
  remains open.
- Do not use `save_original` on an Untitled project.
- Do not kill CST by process name. Use `cst.cleanup_stale_processes` only with
  explicit PIDs and `allow_terminate=true`.
- When existing solver/modeler processes are active, checkpoint the job and
  avoid launching another solve unless the user explicitly approves.

## file-save-and-results

Purpose: save copies, read result trees, export metrics, and avoid stale result
interpretation.

Default sequence:

1. Decide the save policy before running a helper: `no_save` for inspection,
   `save_copy` for generated artifacts, `save_original` only for an existing
   user-approved project.
2. Use `cst.inspect_project` with `include_results=true` to discover result-tree
   paths.
3. Use `cst.result_sanity` before reporting S-parameters, farfield, gain, or
   efficiency as physical conclusions.
4. Record source result paths, run IDs, target frequencies, and whether results
   came from the saved project or a live session.

Rules:

- Treat missing or stale result paths as a blocking uncertainty.
- For passive structures, check that selected S-parameter magnitudes are not
  physically impossible unless active or nonstandard normalization is known.
- Report unverified data as unvalidated data, not as an engineering conclusion.

## solver

Purpose: configure and run CST solvers only after structure, ports, materials,
boundaries, mesh, and monitors are validated.

Default sequence:

1. Build or inspect the structure.
2. Run `cst.inspect_geometry`.
3. Add or verify materials, ports, boundaries, monitors, mesh, and solver setup.
4. Run `cst.inspect_physics_setup`.
5. Run `cst.preflight_resources` and record a `preflight` checkpoint.
6. Start the solver only after review-gated confirmation or explicit
   `full_auto` intent.
7. Record `running`, `done`, `failed`, or `interrupted` checkpoints around the
   solve.
8. Run `cst.result_sanity` before interpreting results.

Macro/doc references to search:

- `Solver Mesh`
- `Time Domain Solver`
- `Frequency Domain Solver`
- `Broad Band Sweep`
- `Farfield Monitor`
- `S-Parameter`

Rules:

- Do not use solver defaults just because they are convenient. Tie solver,
  boundary, mesh, and monitors to the physical structure brief.
- Do not start long solves when preflight reports too many CST processes,
  insufficient memory, low disk, or update-manager modal risk.

## ports

Purpose: choose and create physically correct excitations.

Default sequence:

1. Classify the feed: coax, waveguide, SIW, microstrip, CPW, stripline, lumped
   gap, face source, cable workflow, Floquet, or plane wave.
2. Identify signal conductor, reference conductor or shield, feed dielectric,
   port cross-section, propagation direction, intended mode, and reference
   impedance.
3. Search macros or docs before writing unfamiliar port History:
   `docs.search_macros` with terms such as `DiscretePort`, `Waveguide Port`,
   `Port Mode`, `Target Cut Off`, or `Calculate port extension coefficient`.
4. For distributed feeds, prefer waveguide `Port` on a physical transverse
   cross-section. Use picked-face workflow when practical:
   clear picks, pick the port face, `With Port`, `.Coordinates "Picks"`,
   `.Create`.
5. Use `DiscretePort` only for a physically lumped, electrically short
   two-terminal excitation.
6. Verify with `cst.inspect_physics_setup`, CST tree evidence, and user visual
   review when face IDs/contact cannot be proven from the tree.

Known correct patterns:

- Microstrip waveguide port: extend feed to boundary, include signal trace,
  substrate, reference ground, and a documented air extension. The previous
  successful 77 GHz correction used CST's port-extension macro table and did
  not silently downgrade to `DiscretePort`.
- Coax feed: model inner conductor, dielectric, outer conductor or shield, and
  ground clearance before creating a waveguide `Port` on the coax cross-section.
- Lumped gap: use `DiscretePort` only when the physical source is a short
  two-terminal local feed; record it as a lumped approximation.

Rules:

- Do not replace a failed waveguide/coax/SIW/microstrip port with a
  `DiscretePort` unless the user explicitly accepts the approximation.
- Do not run a solver after port edits until port contacts and reference
  conductors are verified.

## materials

Purpose: define material properties in CST History with units, losses, and
frequency behavior explicit.

Default sequence:

1. List all non-vacuum regions and expected material roles.
2. Search official docs or macros before unfamiliar material models:
   `Material`, `Drude`, `Cole-Cole`, `Graphene`, `Tensor`, `Surface Impedance`,
   `Biological Tissue`.
3. Create material definitions before geometry that references them.
4. Use visible History captions for material definitions.
5. Verify material evidence with `cst.inspect_physics_setup`.

Rules:

- Do not leave unknown dielectric constants, loss tangents, or metal models
  implicit.
- Distinguish PEC, finite conductivity, lossy metal, thin sheet, and surface
  impedance assumptions.
- Keep reusable material probes as recipes or data files instead of probing CST
  repeatedly.

## modeling

Purpose: create parameterized CST geometry that remains readable and editable in
the History tree.

Default sequence:

1. Write a physical structure brief before geometry creation or mutation.
2. Create units first, then CST parameters with `StoreParameter` or
   `StoreParameterWithDescription`.
3. Create materials before material-referencing objects.
4. Add one visible `model3d.add_to_history()` entry per physical object or
   tightly coupled operation.
5. Keep user-tunable dimensions as CST parameter names or CST expressions in
   History code.
6. Rebuild and verify tree evidence before adding ports or running solvers.

Macro/doc references to search:

- `Brick`, `Cylinder`, `Sheet`, `Curve`, `TraceFromCurve`, `Polygon3D`
- `Component.New`
- `Transform`, `WCS`, `Pick`
- demo macros such as `Dipole Antenna`, `Horn antenna`,
  `Microstrip with Bondwire`, `Waveguide Iris Filter`

Rules:

- Do not hide many unrelated solids inside one broad History caption such as
  `create geometry`.
- Do not reference CST parameters before they exist; that can create modal
  prompts.
- If tree-derived inspection cannot prove contact or face IDs, include that as
  review risk before solving.

## boolean

Purpose: make Boolean operations traceable and reversible.

Default sequence:

1. Name the mutation and create or reuse a design record.
2. Create a visible tool body with a `tool_*` name and parameterized dimensions.
3. Verify target object names before Boolean operations.
4. Perform one Boolean operation per History caption when practical.
5. Record target objects, tool objects, created objects, hidden/deleted objects,
   and expected physical effect.
6. Rebuild immediately, then inspect geometry before continuing.

Macro/doc references to search:

- `Boolean`
- `Subtract`
- `Unite`
- `Intersect`
- `Pick`
- `Transform`

Rules:

- Prefer copied projects for destructive Boolean mutations.
- Do not stack more mutations on top of a failed rebuild.
- Do not delete objects whose role is unclear; rename to `bak_*`, hide, or work
  in a copy first.

## process-and-recovery

Purpose: make long CST tasks resumable and avoid repeated manual recovery.

Default sequence:

1. Run process/resource preflight.
2. Record checkpoint `preflight`.
3. Use stage names such as `structure_inspect`, `geometry_mutation`,
   `geometry_verify`, `physics_setup`, `solve`, `result_read`, `sanity`,
   `finalize`.
4. Record `running` before fragile or expensive stages and `done` after
   verification.
5. On interruption, use `cst.recover_job` before rerunning any stage.

Rules:

- If Update Manager warns that license details are required for update checks,
  treat it as a CST configuration/modal issue, not a modeling error.
- If a stage stalls, record `interrupted` or `failed`; do not blindly rerun a
  destructive stage.

## structure-understanding

Purpose: improve the model's understanding of CST objects by building an
external structure state instead of relying on memory.

Default sequence:

1. Extract object inventory: name, component, type, material, bounding evidence,
   History caption, and role.
2. Build a layer/stack map: substrate, metals, dielectric, airbox, and z-levels.
3. Build a conductor graph: expected contacts, intended gaps, grounds,
   shields, signal conductors, vias, pins, and floating metals.
4. Build a feed graph: signal, reference, dielectric, port face or terminal
   points, mode line, and propagation direction.
5. Build a Boolean lineage map: target body, tool body, operation, resulting
   body, and rollback object.
6. Use the structure state to produce a `structure_brief` before mutation,
   ports, or solver setup.

Rules:

- This is a retrieval/checking layer, not neural training. Build the state from
  CST tree evidence, History, generated scripts, and saved records first.
- Fine-tuning should only be considered after many verified examples of
  `project state -> correct structure brief -> correct operation decision` are
  collected.
