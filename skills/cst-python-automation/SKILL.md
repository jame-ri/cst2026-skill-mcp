---
name: cst-python-automation
description: "Use when a user asks about CST Studio Suite or CST-MWS automation, .cst projects, CST-specific antenna/RF simulation setup, editing CST parameters/geometry/ports/boundaries, running CST solvers, reading CST result trees/logs or CST-generated S11/S21/farfield/gain/efficiency results, using CST installed macro/History/VBA examples, or building CST optimization, sweep, surrogate, or ML-data workflows. Avoid triggering for general antenna/RF theory, generic S-parameter plotting, or non-CST simulation work unless CST project/result automation is involved."
---

# CST Python Automation Skill

## Core Split

This skill governs model behavior: how to interpret natural-language CST requests, stay safe, consult official references, record design versions, and report results.

The repository under `CST_API_ROOT` provides the standardized tool layer: macro search, official-document reads, History/VBA pattern extraction, design manifests, and conservative CST Python helper execution. Read `references/local-environment.md` for this machine's cached paths before using absolute paths.

Prefer MCP tools for standardized actions. If MCP coverage is insufficient, fall back to this skill's rules and inspect the repository references directly. Before rediscovering a CST call pattern from macros or official docs, check `references/cst-call-recipes.md` and `references/cst-error-cookbook.md` for existing task recipes and known failure lessons.

For every nontrivial CST electromagnetic model creation, mutation, repair, or solver setup, run the `Electromagnetic Design Gate` in `references/em-design-gates.md`. A project, port, boundary, mesh, or solver setup is not complete until every applicable gate step has an allowed status and evidence. Object existence in the CST tree or History is necessary evidence, not sufficient physical validation.

## Scope

Use this skill for CST Studio Suite workflows involving:

- Launching CST, connecting to a running session, reusing an open project, or opening a `.cst` project
- Editing parameters, materials, geometry, ports, boundaries, monitors, mesh, or solver settings
- Learning `VBA/History/add_to_history` command patterns from installed CST macros
- Reading `S11`, `S21`, farfield, gain, efficiency, currents, result trees, and logs
- Rebuilding, solving, post-processing, or exporting results
- Iterating complex antenna or RF structures with versioned design records
- Running optimization loops, parameter sweeps, surrogate modeling, or ML data workflows

## Trigger Style

Prefer this skill when the request is tied to CST Studio Suite, a `.cst` project, CST macros/History commands, CST result trees, or CST-generated simulation data. Do not use this skill for general antenna/RF theory, generic S-parameter plotting, or non-CST simulation work unless the user explicitly connects the task to CST.

Strong triggers:

- `CST`, `CST Studio Suite`, `CST-MWS`
- `.cst`, `open project`, `launch CST`, `connect CST`, `result tree`
- `macro`, `VBA`, `History`, `RunScript`, `add_to_history` in a CST context
- `open .cst`, `launch CST`, `connect CST`, `modify geometry`

Contextual triggers only when CST is implied or stated:

- `antenna`, `RF`, `microwave`, `S11`, `S21`, `farfield`, `gain`, `efficiency`
- `parameter sweep`, `optimization`, `surrogate`, `ML`, `deep learning`

## Tool Priority

1. If `cst2026-mcp` is installed, use MCP tools for standardized actions first.
2. Use `docs.search_macros`, `docs.read_macro`, and `history.extract_pattern` for macro-library work.
3. Use `docs.search_official_docs` and `docs.read_official_doc` for official references.
4. Use `records.create_variant` and `records.append_operation` for design records.
5. Use `cst.inspect_project`, `cst.inspect_geometry`, `cst.inspect_physics_setup`, and `cst.result_sanity` for read-only structure, setup, and result checks before modeling, solving, or interpreting results.
6. Use `cst.process_status`, `cst.preflight_resources`, `cst.job_checkpoint`, `cst.recover_job`, and `cst.cleanup_stale_processes` to guard long CST jobs against stuck processes, memory pressure, and interrupted multi-step runs.
7. Use `cst.closed_start`, `cst.close_project`, and `cst.live_modify_parameter` for controlled CST execution; these default to `execute=false` and should only execute when user intent is clear.
8. Use `knowledge.list_categories`, `knowledge.get_recipe`, and `knowledge.search_lessons` when available to retrieve CST call recipes and known error lessons before re-searching raw macros.
9. Before rediscovering CST executables or documentation paths, read `references/local-environment.md` and check `CST_PYTHON_EXE`, `CST_API_ROOT`, `CST_MCP_ROOT`, `CST_OFFICIAL_DOCS`, and `CST_MACRO_LIBRARY`.
10. If MCP is unavailable, read repository references directly and write Python/VBA/History scripts under the same safety rules.

In Codex tool lists, the same MCP tools may be exposed with underscore names or an MCP namespace. Use the actually available callable name:

| README/MCP name | Codex callable name |
| --- | --- |
| `docs.search_macros` | `docs_search_macros` |
| `docs.read_macro` | `docs_read_macro` |
| `docs.search_official_docs` | `docs_search_official_docs` |
| `docs.read_official_doc` | `docs_read_official_doc` |
| `history.extract_pattern` | `history_extract_pattern` |
| `records.create_variant` | `records_create_variant` |
| `records.append_operation` | `records_append_operation` |
| `cst.inspect_project` | `cst_inspect_project` |
| `cst.inspect_geometry` | `cst_inspect_geometry` |
| `cst.inspect_physics_setup` | `cst_inspect_physics_setup` |
| `cst.result_sanity` | `cst_result_sanity` |
| `cst.process_status` | `cst_process_status` |
| `cst.preflight_resources` | `cst_preflight_resources` |
| `cst.job_checkpoint` | `cst_job_checkpoint` |
| `cst.recover_job` | `cst_recover_job` |
| `cst.cleanup_stale_processes` | `cst_cleanup_stale_processes` |
| `cst.closed_start` | `cst_closed_start` |
| `cst.close_project` | `cst_close_project` |
| `cst.live_modify_parameter` | `cst_live_modify_parameter` |
| `knowledge.list_categories` | `knowledge_list_categories` |
| `knowledge.get_recipe` | `knowledge_get_recipe` |
| `knowledge.search_lessons` | `knowledge_search_lessons` |

## Reference Priority

Read these sources as needed:

Resolve `$env:...` paths from the current shell when they exist; if they are unset, use the cached values in `references/local-environment.md`.

1. `references/local-environment.md` for this machine's cached CST Python, CST executable, CST API, MCP, official docs, and macro-library paths.
2. `references/cst-call-recipes.md` for default workflows by task category: project management, file/result handling, solver, ports, materials, modeling, Boolean operations, process recovery, and structure understanding.
3. `references/em-design-gates.md` for mandatory electromagnetic design gates, evidence standards, stop rules, no-simulation review packages, the gate ledger template, and the static validator command.
4. `references/cst-error-cookbook.md` for known CST automation failure modes and the correct next action.
5. `$env:CST_MCP_ROOT\README.md`
6. `$env:CST_OFFICIAL_DOCS\python\`
7. `$env:CST_OFFICIAL_DOCS\python_cst_libraries\cst\`
8. `$env:CST_OFFICIAL_DOCS\vba-3d\`
9. `$env:CST_OFFICIAL_DOCS\vba-des\`
10. `$env:CST_OFFICIAL_DOCS\advanced\`
11. `$env:CST_MACRO_LIBRARY\macro-inventory.csv`
12. `$env:CST_MACRO_LIBRARY\cst-macro-usage.en.md`
13. `$env:CST_MACRO_LIBRARY\macro-catalog.en.md`
14. `$env:CST_API_ROOT\domain-guides\design-evolution.en.md`
15. `$env:CST_API_ROOT\domain-guides\geometry-mutation.en.md`
16. `$env:CST_API_ROOT\domain-guides\result-diagnosis.en.md`
17. `$env:CST_API_ROOT\domain-guides\optimization-ml-data.en.md`

## Operating Rules

1. Inspect the current project, parameters, result tree, or existing record before proposing changes.
2. Prefer official CST references, installed macros, and repository examples over guesswork.
3. Use `cst.interface` for live sessions and `cst.results` for saved result reads.
4. Use `model3d.add_to_history()` for geometry, ports, boundaries, mesh, monitors, and solver setup, and follow the stricter `History Tree Requirements` below.
5. Use the cached `CST_PYTHON_EXE` path when running local CST Python scripts. If the cached path fails, verify the path once and use a task-local override or current-process environment variable. Update persistent Windows user environment variables or `references/local-environment.md` only when the user explicitly asks for a durable path update.
6. If a CST VBA/History command is unfamiliar, search the macro library and extract the smallest controllable snippet instead of batch-running full interactive macros as black boxes.
7. Do not save the original project by default; destructive edits, structure deletion, long simulations, and optimization loops should use a copied project or job copy.
8. Complex structure evolution must record `design_id`, `parent_design_id`, operations, metrics, logs, dataset versions, and surrogate versions.
9. Only use APIs, method names, and parameter names confirmed in official docs, installed macros, or repository code.
10. If an API detail is uncertain, verify it first instead of filling the gap with assumptions.
11. Use a bounded inspect-mutate-verify-checkpoint loop for solver automation. Avoid large one-shot scripts that create geometry, assign physics, run solvers, and interpret results without intermediate state checks.
12. For long solves, sweeps, optimization, or ML data generation, run a resource preflight, record job checkpoints, and plan recovery before launching CST execution.
13. Treat CST GUI modal dialogs as automation blockers. Before starting CST, check `cst.process_status` / `cst.preflight_resources`; if the Update Manager reports `License details are required to check for updates`, identify it as an automatic-update configuration issue, not a modeling error. The durable fix is to disable automatic software updates in CST Preferences or repair Update Manager license settings.
14. Never rely on `DesignEnvironment.close()` to decide how unsaved projects should close. For every helper-owned new or temporary project, explicitly apply the close/save policy first: `no_save` calls `Project.close()`, `save_copy` calls `Project.save(copy_path, ...)` then `Project.close()`, and `save_original` is only allowed for a project that already has a saved filename. Only after all helper-owned projects are closed may the script call `DesignEnvironment.close()`.
15. Treat the electromagnetic design process as a gate, not a narrative checklist. Every CST create/modify/repair task must record gate statuses using only `pass`, `not_applicable`, `blocked`, or `not_executed`. Do not continue past a critical gate or call the model complete when physical structure, geometry/connectivity, port, boundary/background, solver/mesh, History, save policy, or requested simulation state lacks evidence. When a JSON gate ledger is created, run `scripts/validate_em_gate_ledger.py` before delivery and report failures as blockers instead of completion.

## Modal Dialog And Close Policy

CST automation must be written so it can finish without a human clicking modal dialogs.

- Update Manager startup popup: if CST shows `License details are required to check for updates`, report it as a known CST automatic-update/license configuration popup. Do not keep retrying modeling commands as if geometry failed. Prefer asking the user to disable automatic software updates under CST `File > Options > Preferences` or to repair Update Manager license details.
- Save confirmation popup: avoid `Do you want to save changes to 'Untitled_0.cst'?` by closing helper-owned projects explicitly. Use `Project.close()` for deliberate no-save scratch projects. Use `Project.save(path, include_results, allow_overwrite)` before `Project.close()` when the artifact must be preserved.
- New project rule: a script that calls `new_mws()` or creates an untitled project must either save it to an explicit `.cst` path before closing, or close it with `Project.close()` in a `finally` block. Do not leave untitled projects open after material probes, geometry probes, or failed modeling attempts.
- Existing user project rule: do not close or save a user-open project unless the user requested that exact operation. Prefer `save_copy` for generated variants and `no_save` for inspections and reversible tests.
- Close ordering: project first, DesignEnvironment second. Do not call `de.close()` while an unsaved helper-owned project is still open.
- If a modal already appears and blocks automation, stop the CST stage, report the dialog text if known, and ask for UI action or use only an explicit project/PID cleanup path. Do not kill CST by process name.

## Error Diagnosis And Repair Memory

When CST modeling, validation, execution, or result extraction fails, do not blindly retry. First classify the failure source, then repair the smallest cause and record the lesson before continuing.

Use this loop:

```text
validation/runtime error
-> classify error source
-> decide whether it is model physics, CST command/calling, port/setup, or result extraction
-> generate the smallest repair action
-> record error, diagnosis, repair, and outcome
-> reuse the lesson to avoid repeating the same error
```

Error classes:

| Error class | Meaning | Typical examples |
| --- | --- | --- |
| `model_physics_error` | The electromagnetic structure is physically invalid | disconnected feed, signal-ground short, missing reference ground, unintended floating conductor |
| `cst_command_error` | The CST Python, History, VBA, object naming, or API call is wrong | undefined parameter, invalid object name, failed Boolean operation, unsupported method |
| `port_setup_error` | The excitation or simulation setup does not match the intended feed physics | wrong CPW port section, missing mode line, lumped port used for distributed feed |
| `result_extraction_error` | The solve may have run, but requested data cannot be read or trusted | wrong result-tree path, missing monitor, frequency mismatch |
| `environment_error` | CST, license, modal dialog, file lock, memory, or process state blocks execution | Update Manager popup, stale process, insufficient memory |

Repair rules:

- Inspect the validation report, CST message log, result tree, project state, and prior records before generating a repair.
- Decide whether the problem is a model-physics issue or a tool-calling/instruction issue; do not mix them.
- Record `error_signature`, `error_class`, `diagnosis`, `repair_action`, `repair_status`, and whether the same error repeated.
- If the same error repeats, search known lessons or the error cookbook before trying another repair.
- Count still-unresolved errors as failed modeling or failed CST runs; do not hide them behind a successful later run.

## Requirements Intake Gate

When the user asks to create, modify, solve, optimize, or diagnose a CST model, first normalize the request before taking modeling or solver actions.

Ask concise targeted questions when the request does not already specify:

- task type: create new project, modify existing project, inspect/debug, run solver, read results, optimize, or generate a dataset
- project source: existing `.cst` path, template/project copy policy, or whether a new project should be created
- physical structure to model: topology, coordinate system, units, dimensions, layers, materials, conductors, feeds, ports, boundaries, frequency band, and intended metrics
- modeling scope: which parts are mandatory, which parts may be simplified, and which values may be assumed
- automation mode: `full_auto` for unattended modeling/ports/solver/results, or `review_gated` for user confirmation before simulation
- output expectation: CST project only, plots, extracted metrics, manifest, exported data, or a written diagnosis

Default to `review_gated` unless the user explicitly asks for a fully automatic/unattended workflow. Record `automation_mode` and the key assumptions before modifying geometry or running a solver.

For `review_gated` workflows, do not run the solver immediately after modeling. After geometry is created and ports are added, but before simulation, stop and ask the user to confirm that the model and port setup are physically correct. Provide a compact review package: structure brief, materials, object/component list or tree evidence, port type and location, boundary/solver plan, assumptions, and known unchecked items. Run simulation only after the user confirms or explicitly switches to `full_auto`.

If the user requests `full_auto`, still apply the Physical Structure Gate, Geometry Invariants, Material/Boundary/Solver Gate, and Result Sanity Gate. In full-auto mode, record every assumption and prefer conservative defaults over hidden guesses.

## Physical Structure Gate

Do not create or modify geometry, ports, boundaries, materials, mesh, or solver settings until the physical structure is understood well enough to write a compact structure brief. For existing `.cst` projects, inspect the project first instead of reconstructing the intended structure from memory.

Before modeling or mutating a nontrivial structure, state or record:

- physical problem and intended observable, for example `S11`, gain, efficiency, field distribution, or eigenmode
- coordinate system, unit system, frequency band, and which direction is propagation or radiation
- layer stack or 3D topology: every substrate, metal layer, air/vacuum region, cavity, via/pin, feed line, connector, shield, aperture, slot, and ground
- material for each physical region, distinguishing known values from assumptions
- electrical connectivity: which conductors touch, which are isolated, which are ground/reference, and which are intentionally floating
- feed topology: signal conductor, return/shield/ground conductor, feed dielectric, port cross-section or terminal points, and whether excitation is distributed or lumped
- boundary meaning: open/radiation, electric/magnetic symmetry, periodic/Floquet, PEC/PMC walls, or waveguide aperture
- dimensions supplied by the user versus inferred dimensions

Stop and ask a targeted question, inspect the project, or read a reference when any missing detail changes topology, material assignment, electrical connectivity, excitation, boundary condition, or result interpretation. Do not infer missing physical parts from an antenna name, paper title, or common template unless the assumption is explicitly recorded and harmless to the requested task.

## Geometry Invariants

After creating or modifying geometry, verify the physical structure before adding ports or running a solver:

- all expected solids, sheets, components, and materials exist with intentional names
- bounding boxes, layer heights, substrate thicknesses, conductor thicknesses, clearances, and slot/gap dimensions match the structure brief
- Boolean operations, picks, transforms, mirrors, and arrays did not delete, merge, invert, or detach unintended objects
- conductors that should touch have real contact or overlap; conductors that should be isolated have a nonzero intended gap
- ground/reference conductors are present and continuous where the feed requires them
- vias, pins, probes, shields, and feed lines connect the intended layers and do not short unintended metals
- dielectric regions enclose the intended feed/field region and do not overwrite metal volumes
- airbox, ports, and boundary planes sit outside or on the intended physical cross-sections, not through active geometry unless deliberately modeled
- symmetry or periodic cuts are valid for the actual geometry and excitation phase

If any invariant cannot be checked from CST state, add an explicit warning and avoid interpreting simulation results as physically validated.

## Material, Boundary, And Solver Gate

Do not run a solver until material assignments, boundary conditions, mesh intent, monitors, and solver type match the physical structure brief.

Before solving, verify:

- every non-vacuum region has the intended material, units, conductivity or loss model, permittivity/permeability, and frequency dependence; unknown materials remain explicit assumptions
- metals use the intended model: PEC, finite conductivity, lossy metal, thin sheet, surface impedance, or imported material
- background material, airbox, and open/PML/radiation distance are consistent with the frequency band and radiator or waveguide size
- boundaries encode the physics: open/radiation for antennas, PEC/PMC/symmetry only when fields and excitation satisfy the symmetry, periodic/Floquet only for valid unit-cell phase conditions, and waveguide walls/apertures only where physically present
- solver choice matches the problem: time domain, frequency domain, eigenmode, integral equation, periodic/Floquet, cable, or circuit co-simulation
- frequency range, excitation bandwidth, monitors, farfield setup, S-parameter normalization, and port mode count are sufficient for the requested metric
- mesh strategy resolves the smallest critical features: gaps, slots, conductor thickness, via/pin radius, feed dielectric, port cross-section, skin depth when relevant, and high-field corners
- local mesh refinements or adaptive convergence criteria are stated when tiny geometric details dominate the result

Stop before solving when the solver type, boundary meaning, material values, or mesh resolution are chosen from convenience rather than physics. If a default is used, record why the default is valid for this structure.

## Parameterization Rules

- Create CST parameters before any history command references them. Use the order: units first, `StoreParameter` / `StoreParameterWithDescription` next, then frequency range, materials, geometry, ports, mesh, monitors, and solver settings. Referencing an undefined parameter can open a modal CST prompt and block automation.
- Put all user-tunable model values in the CST parameter list, including substrate heights, material constants, patch dimensions, slot dimensions, via/pin radii, feed/coax dimensions, array pitch, element count, and solver frequency bounds.
- Use parameter names and CST expressions in geometry history instead of baking Python-computed numbers into `.Xrange`, `.Yrange`, `.Zrange`, `.Radius`, material epsilon/tanD, or solver frequency fields whenever the value is meant to be manually editable.
- Store derived coordinates or layer levels as parameters when they are reused, for example `z_top_min`, `z_top_max`, `x_e1`, `x_e2`, etc. This keeps CST rebuilds predictable after manual edits.

## History Tree Requirements

Treat CST History visibility as a deliverable, not an implementation detail.

- For every created, modified, deleted, or transformed CST object, write a visible `model3d.add_to_history()` entry with a specific caption. Do this for materials, bricks/sheets/curves, Boolean operations, ports, boundaries, mesh settings, monitors, solver settings, picks, transforms, and result-setup commands.
- Prefer one physical object or one tightly coupled operation per History entry. Do not hide many unrelated solids inside one broad entry such as `create geometry` when the user is expected to inspect or edit the History tree. Use captions like `define brick: stack:lower_dielectric`, `define brick: metals:bottom_ground_yneg`, `define waveguide port: microstrip_feed_xmin`, and `define monitor: e-field 10 GHz`.
- Do not create CST model geometry through direct API calls, imported transient geometry, or helper-side side effects unless an equivalent visible History entry is also written and verified.
- Create CST parameters before History commands reference them. Keep editable dimensions as parameter names or CST expressions in the History code instead of substituting opaque Python-computed numbers.
- After saving a generated or modified project, verify that the History was persisted before claiming success. At minimum, inspect the saved project folder's `Model/3D/ModelHistory.json` or use an available CST inspection tool, and confirm the expected captions and command types are present.
- If the user specifically asks to inspect the CST GUI History tree, open the project and report whether the visible tree contains the expected modeling entries. Do not treat `add_to_history()` success alone as proof of GUI-visible History.
- If History entries are missing, hidden, overly collapsed, or only present in a side file, stop and rebuild or repair the project before running a solver or presenting the model as complete.
- In review-gated workflows, include History verification in the review package: list the key captions found, the verification method used, and any unchecked GUI visibility risk.

## Port Setup Rules

- Before defining any port, explicitly classify the feed and conductors: feed type, signal conductor, reference conductor or shield, dielectric region, physical port cross-section, intended mode, and whether the feed is distributed or lumped.
- Choose the CST port object from the physical feed, not from convenience. Check CST Help or installed macro examples when unsure; the main objects are `Port` for waveguide ports, `DiscretePort` for point/edge lumped ports, `DiscreteFacePort` for face-based lumped ports, and `CablePort` for CST cable-model feeds.
- A port tree item, a History `Port` command, or a selected face only proves that CST has a port object. It does not prove physical correctness. The port gate passes only when the feed classification, selected CST object, physical transverse section or lumped terminals, reference conductor, dielectric inclusion, orientation, mode line/calibration, and evidence source are all recorded and consistent.
- Use this selection guide:

| Feed structure | Preferred CST feed | Required setup |
| --- | --- | --- |
| Coaxial connector, SMPM, probe with inner conductor + dielectric + outer conductor/shield | Waveguide `Port` on the coax cross-section | Model inner conductor, dielectric, outer conductor/shield, and ground clearance first. Pick the coax dielectric/open cross-section with `PickFaceFromId` or `PickFaceFromPoint`, then create `With Port` using `.Coordinates "Picks"`. Add a mode line from inner conductor to shield when needed. Do not silently replace this with `DiscretePort`. |
| Rectangular/circular metallic waveguide, horn throat, waveguide launcher | Waveguide `Port` on the terminal waveguide aperture | Pick the end face or use an appropriate boundary-aligned plane. Set orientation along propagation and number of modes from the desired TE/TM modes. |
| SIW feed or substrate-integrated waveguide section | Waveguide `Port` on the SIW cross-section | Model top/bottom metal, substrate, via fences/side walls, and aperture plane. Excite the SIW guided mode at the section cross-section, not a point inside the guide. |
| Microstrip, CPW, stripline, grounded coplanar feed line | Waveguide `Port` on a transverse line cross-section for distributed-line excitation | Include signal trace, dielectric, and all relevant reference grounds in the port face/span. Add mode line from signal conductor to reference ground. Use a discrete port only when intentionally approximating a short lumped feed. |
| Two-terminal lumped source, small gap, local feed pin to ground, point-to-point excitation | `DiscretePort` | Define the two physical terminal points/edges on conductors. Use this only when the intended excitation is lumped and electrically short; record that it is a lumped approximation. |
| Face-based lumped excitation on finite conductor faces | `DiscreteFacePort` | Use only when a face lumped source is physically intended and solver support is confirmed in CST Help. Remember CST may replace it with a discrete edge port for unsupported solvers. |
| Cable harness or CST cable-model excitation | `CablePort` | Use only when the model is built with CST cable objects/cable workflow, after checking the CablePort help. Do not use it as a generic coax substitute. |
| Periodic unit cell / Floquet excitation or incident plane wave | Floquet port or `PlaneWave`, not a normal lumped feed | Use only for the corresponding boundary/excitation physics and do not report ordinary multiport S-parameters unless the setup supports them. |

- Prefer the CST UI-equivalent picked-face workflow for waveguide-style ports: create or expose the planar port face, clear picks, pick the face, then create `With Port` using `.Coordinates "Picks"` and `.Create`.
- For microstrip, CPW, stripline, and grounded coplanar feeds, the waveguide `Port` must be placed on the line's transverse feed cross-section, not merely on the outer calculation boundary for convenience and not merely on the metal trace end face. The port span or picked aperture must include the signal conductor, dielectric region, all relevant reference grounds, and needed air region. Add a mode line from signal conductor to reference ground. If this cannot be created or verified, stop with `port_setup_error` and do not present the project as complete.
- Do not silently fall back from a distributed feed (`Port`) to a lumped feed (`DiscretePort` or `DiscreteFacePort`). If the intended waveguide/coax/SIW/microstrip port cannot be created, stop, inspect the picked face and history commands, and fix the physical port definition.
- Define mode lines, potentials, port extensions, reference planes, and multipin settings only after confirming the relevant commands in CST Help or installed macros. Keep initial port history minimal and inspectable before adding advanced settings.
- Record port decisions in the build summary: `feed_type`, chosen CST port object, signal/reference conductors, picked face or point coordinates, mode line, and the help/macro source used.

## Decision Flow

- Intake: clarify modeling requirements, project source, output expectations, and `automation_mode`; default to `review_gated` unless the user explicitly requests full automation. Open an electromagnetic design gate ledger for nontrivial create/modify/repair/setup work.
- Connect/open CST: run `cst.process_status` and `cst.preflight_resources` first for long jobs; list existing sessions and open projects; use `cst.inspect_project` for read-only state discovery and `cst.closed_start` or equivalent scripts for cold start.
- Modify parameters: read the original value, write the test value, rebuild, optionally pause for observation, restore by default, and do not save.
- Modify geometry: pass the Physical Structure Gate, use `cst.inspect_geometry` when an existing project is involved, create a design record, state the hypothesis, then apply the smallest History mutation.
- Add/delete structures: specify target objects, materials, coordinate systems, physical connectivity, boolean operations, and rollback strategy.
- Review gate: in `review_gated` mode, after geometry and ports are created but before simulation, present the structure/port review package and wait for user confirmation.
- Assign materials/boundaries/solver: pass the Material, Boundary, And Solver Gate, using `cst.inspect_physics_setup` when possible, before running or interpreting a solve.
- Read results: discover result-tree paths before reading S-parameters, farfield, efficiency, gain, logs, or exported tables; use `cst.result_sanity` before turning numerical values into physical conclusions.
- Diagnose and repair errors: classify the failure source, apply the smallest repair, and record the repair memory before continuing.
- Tune response: start from a physical mechanism hypothesis, scan likely sensitive parameters, extract response sensitivity, then fine tune.
- Optimize or use ML: treat CST as the expensive ground-truth evaluator and record every trial input, output, project copy, log, and dataset version; optimizers and samplers provide candidate points, not physical explanations.
- Finalize: apply the declared save/close policy before ending automation. Close helper-owned temporary projects with `Project.close()` or save to an explicit copy path first; only close the DesignEnvironment after helper-owned projects are already closed.

## Long-Run Reliability

For CST solves, sweeps, optimization loops, or any task that may outlive the current Codex turn, use a resumable job pattern.

Before execution:

- Run `cst.process_status` and `cst.preflight_resources` to check existing CST processes, memory, and disk space.
- Check the Update Manager warning state reported by preflight. If automatic update/license popups are likely, record the warning and avoid treating startup UI interruption as a CST modeling failure.
- Record a `preflight` checkpoint with `cst.job_checkpoint`.
- Prefer a copied project or job copy; do not depend on unsaved GUI state for recovery.
- Define stage names before running: `preflight`, `structure_inspect`, `geometry_mutation`, `geometry_verify`, `physics_setup`, `solve`, `result_read`, `sanity`, `error_diagnosis`, `sensitivity_scan`, `fine_tuning`, and `finalize`.

During execution:

- Record `running` and `done` checkpoints around every expensive or fragile stage.
- Keep solver jobs bounded by timeout and monitor process/resource status between stages.
- If a stage stalls, mark it `interrupted` or `failed`; do not silently rerun a destructive stage without checking project state.
- Do not start a new CST instance when preflight reports too many CST-related processes or insufficient memory.
- In script `finally` blocks, close helper-owned projects before closing the DesignEnvironment. A failed script must still leave the close policy explicit.

Recovery:

- Use `cst.recover_job` to identify the last completed checkpoint and the safest next stage.
- Use `cst.process_status` before deciding whether a CST process is still useful, stalled, or stale.
- Use `cst.cleanup_stale_processes` only with explicit PIDs and `allow_terminate=true`; never kill CST by name or because it looks idle.
- After recovery, rerun the relevant inspect or sanity gate before interpreting results.

## Result Sanity Gate

Before presenting CST outputs as engineering conclusions, check that the result is physically and numerically plausible.

For S-parameter and port results, verify:

- the requested result-tree paths exist and correspond to the intended excitation and mode
- port mode names, reference impedance, renormalization, de-embedding, and calibration plane are known or reported as assumptions
- passive structures do not show impossible gain, for example `|S11| > 0 dB` or nonphysical S-parameter magnitudes, unless active/nonstandard normalization is explicitly involved
- reciprocity, symmetry, or isolation expectations are checked when the structure should satisfy them

For farfield, gain, and efficiency results, verify:

- farfield monitor frequency matches the requested band or design frequency
- accepted power, radiated power, total efficiency, realized gain, and directivity are mutually plausible
- main beam direction, polarization, and nulls make sense for the physical structure and feed orientation
- reported gain is not interpreted without stating whether it is gain, realized gain, or directivity

For solver health, verify:

- CST messages/logs do not contain unresolved port, mesh, material, boundary, convergence, or license warnings
- adaptive convergence or mesh refinement met the intended tolerance, or the lack of convergence is reported
- result changes from a parameter or geometry edit are compared to the previous design when available

If sanity checks fail or cannot be performed, report the numerical output as unvalidated data, not as a physical conclusion.

## Physics-Guided Sensitivity Tuning

Do not frame antenna response tuning as blind parameter optimization. Use CST sweeps as physical probes that reveal how geometry changes affect resonances, matching, current distribution, gain, patterns, and efficiency.

Use this loop:

```text
physical mechanism hypothesis
-> select likely sensitive parameters
-> one-at-a-time or low-dimensional parameter scans
-> extract response sensitivity
-> update parameter-mode relationship
-> perform fine tuning around sensitive parameters
```

Before scanning, state the expected mechanism and candidate sensitive parameters. Examples:

| Observed response | Physical interpretation | Candidate parameters |
| --- | --- | --- |
| low-band resonance too high | low-band current path is electrically short | meander length, slot length, ground extension |
| high-band resonance too high | high-band branch or slot is electrically short | high-band branch length, slot length, coupling position |
| matching is shallow | coupling or feed impedance is not balanced | feed width, CPW gap, coupling length, branch location |
| both bands shift together | feed/ground coupling dominates both modes | CPW geometry, ground size, common feed junction |
| S11 is good but efficiency is poor | lossy current concentration or excessive meander path | strip width, loss path, substrate/material choice |

Sensitivity scan rules:

- Prefer one-at-a-time or low-dimensional scans around physically plausible bounds before any high-dimensional optimization.
- For each scan, record the parameter, range, step, fixed variables, CST project copy, S11 shift, gain/efficiency change, current or pattern evidence, and physical interpretation.
- Build a `parameter_mode_map` that links each tunable dimension to the affected resonance, matching depth, bandwidth, gain, efficiency, or radiation mode.
- Fine tune only after the coarse sensitivity relationship is known; use smaller steps around the sensitive region.
- If a parameter change improves S11 while degrading gain, efficiency, pattern, or current sanity, report the tradeoff instead of accepting the match alone.
- Use optimizers, surrogate models, or samplers only as candidate generators; convert their samples into a physical sensitivity explanation before presenting the result.

## Output Contract

When a task modifies a project, runs or plans CST execution, creates a design record, reads simulation results, or generates artifacts, finish with this compact record:

```yaml
project_path: used or generated CST project
save_policy: no_save | save_copy | save_original
design_id: current structure version
parent_design_id: previous structure version or null
automation_mode: full_auto | review_gated
user_confirmation: required, received, skipped_full_auto, or not_applicable
physical_structure: topology, feed, materials, boundaries, and assumptions checked before modeling
physics_setup: material, boundary, mesh, monitor, and solver choices checked before solving
mcp_tools: MCP tools called during the task
operations: parameter/modeling/simulation/result-reading steps
metrics: extracted values with source paths
sanity_checks: result-tree, port, farfield, efficiency, convergence, and log checks
error_diagnosis: error classes, causes, repair actions, repeated errors, and status
repair_memory: lessons recorded to avoid repeating the same modeling or calling error
sensitivity_scan_results: parameter ranges, response shifts, and CST evidence from scans
parameter_mode_map: relationship between parameters, structural changes, resonances, matching, gain, efficiency, and modes
fine_tuning_trace: final small-step updates derived from the sensitivity map
job_status: current resumable job status
checkpoints: preflight/running/done/failed/interrupted/recovered stage records
resource_guard: process, memory, disk, timeout, and cleanup checks
modal_dialogs: Update Manager warnings, save prompts avoided, or blocking dialogs encountered
close_policy: project close/save actions performed before ending CST automation
recovery: last completed checkpoint and resume recommendation
logs: Model.log/output.json/outputDS.json paths
artifacts: generated files, datasets, plots, manifests, model cards
versions: dataset_version, surrogate_version, CST project copy version
source_macros: CST installed macro paths used as references or adapted sources
warnings: assumptions, skipped steps, risks
errors: failures and recovery attempts
em_design_gate: per-step status, evidence, pass condition, unchecked risk, and blockers from `references/em-design-gates.md`
```

For pure advice or small CST reference questions, answer briefly instead. Include the decision, the CST source or macro checked, and any uncertainty or risk; do not force the full YAML report unless it helps the user continue the workflow.
