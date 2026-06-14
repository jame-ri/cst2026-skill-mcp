---
name: cst-python-automation
description: Use when a user asks about CST Studio Suite, CST-MWS, antenna or RF simulation, opening or launching a .cst project, editing parameters or geometry, defining ports or boundaries, running solvers, reading S11/S21/farfield/gain/efficiency/logs, using CST installed macro examples, or building an optimization or ML-driven CST workflow.
---

# CST Python Automation Skill

## Core Split

This skill governs model behavior: how to interpret natural-language CST requests, stay safe, consult official references, record design versions, and report results.

`D:\CSTapi\mcp\` provides the standardized tool layer: macro search, official-document reads, History/VBA pattern extraction, design manifests, and conservative CST Python helper execution.

Prefer MCP tools for standardized actions. If MCP coverage is insufficient, fall back to this skill's rules and inspect the repository references directly.

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

Prefer this skill when the user mentions:

- `CST`, `CST Studio Suite`, `CST-MWS`
- `antenna`, `RF`, `microwave`, `S11`, `farfield`, `gain`, `efficiency`
- `parameter sweep`, `optimization`, `surrogate`, `ML`, `deep learning`
- `macro`, `VBA`, `History`, `RunScript`, `add_to_history`
- `open .cst`, `launch CST`, `connect CST`, `modify geometry`

## Tool Priority

1. If `cst2026-mcp` is installed, use MCP tools for standardized actions first.
2. Use `docs.search_macros`, `docs.read_macro`, and `history.extract_pattern` for macro-library work.
3. Use `docs.search_official_docs` and `docs.read_official_doc` for official references.
4. Use `records.create_variant` and `records.append_operation` for design records.
5. Use `cst.closed_start` and `cst.live_modify_parameter` for controlled CST execution; these default to `execute=false` and should only execute when user intent is clear.
6. Before rediscovering CST executables or documentation paths, read `references/local-environment.md` and check `CST_PYTHON_EXE`, `CST_API_ROOT`, `CST_MCP_ROOT`, `CST_OFFICIAL_DOCS`, and `CST_MACRO_LIBRARY`.
7. If MCP is unavailable, read repository references directly and write Python/VBA/History scripts under the same safety rules.

## Reference Priority

Read these sources as needed:

1. `references/local-environment.md` for this machine's cached CST Python, CST executable, CST API, MCP, official docs, and macro-library paths.
2. `D:\CSTapi\mcp\README.md`
3. `D:\CSTapi\official-docs\python\`
4. `D:\CSTapi\official-docs\python_cst_libraries\cst\`
5. `D:\CSTapi\official-docs\vba-3d\`
6. `D:\CSTapi\official-docs\vba-des\`
7. `D:\CSTapi\official-docs\advanced\`
8. `D:\CSTapi\macro-library\macro-inventory.csv`
9. `D:\CSTapi\macro-library\cst-macro-usage.en.md`
10. `D:\CSTapi\macro-library\macro-catalog.en.md`
11. `D:\CSTapi\domain-guides\design-evolution.en.md`
12. `D:\CSTapi\domain-guides\geometry-mutation.en.md`
13. `D:\CSTapi\domain-guides\result-diagnosis.en.md`
14. `D:\CSTapi\domain-guides\optimization-ml-data.en.md`

## Operating Rules

1. Inspect the current project, parameters, result tree, or existing record before proposing changes.
2. Prefer official CST references, installed macros, and repository examples over guesswork.
3. Use `cst.interface` for live sessions and `cst.results` for saved result reads.
4. Use `model3d.add_to_history()` for geometry, ports, boundaries, mesh, and solver setup.
5. Use the cached `CST_PYTHON_EXE` path when running local CST Python scripts. If the cached path fails, update the environment variable and `references/local-environment.md` after one verified rediscovery.
6. If a CST VBA/History command is unfamiliar, search the macro library and extract the smallest controllable snippet instead of batch-running full interactive macros as black boxes.
7. Do not save the original project by default; destructive edits, structure deletion, long simulations, and optimization loops should use a copied project or job copy.
8. Complex structure evolution must record `design_id`, `parent_design_id`, operations, metrics, logs, dataset versions, and surrogate versions.
9. Only use APIs, method names, and parameter names confirmed in official docs, installed macros, or repository code.
10. If an API detail is uncertain, verify it first instead of filling the gap with assumptions.

## Parameterization Rules

- Create CST parameters before any history command references them. Use the order: units first, `StoreParameter` / `StoreParameterWithDescription` next, then frequency range, materials, geometry, ports, mesh, monitors, and solver settings. Referencing an undefined parameter can open a modal CST prompt and block automation.
- Put all user-tunable model values in the CST parameter list, including substrate heights, material constants, patch dimensions, slot dimensions, via/pin radii, feed/coax dimensions, array pitch, element count, and solver frequency bounds.
- Use parameter names and CST expressions in geometry history instead of baking Python-computed numbers into `.Xrange`, `.Yrange`, `.Zrange`, `.Radius`, material epsilon/tanD, or solver frequency fields whenever the value is meant to be manually editable.
- Store derived coordinates or layer levels as parameters when they are reused, for example `z_top_min`, `z_top_max`, `x_e1`, `x_e2`, etc. This keeps CST rebuilds predictable after manual edits.

## Port Setup Rules

- Before defining any port, explicitly classify the feed and conductors: feed type, signal conductor, reference conductor or shield, dielectric region, physical port cross-section, intended mode, and whether the feed is distributed or lumped.
- Choose the CST port object from the physical feed, not from convenience. Check CST Help or installed macro examples when unsure; the main objects are `Port` for waveguide ports, `DiscretePort` for point/edge lumped ports, `DiscreteFacePort` for face-based lumped ports, and `CablePort` for CST cable-model feeds.
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
- Do not silently fall back from a distributed feed (`Port`) to a lumped feed (`DiscretePort` or `DiscreteFacePort`). If the intended waveguide/coax/SIW/microstrip port cannot be created, stop, inspect the picked face and history commands, and fix the physical port definition.
- Define mode lines, potentials, port extensions, reference planes, and multipin settings only after confirming the relevant commands in CST Help or installed macros. Keep initial port history minimal and inspectable before adding advanced settings.
- Record port decisions in the build summary: `feed_type`, chosen CST port object, signal/reference conductors, picked face or point coordinates, mode line, and the help/macro source used.

## Decision Flow

- Connect/open CST: list existing sessions and open projects first; use `cst.closed_start` or equivalent scripts for cold start.
- Modify parameters: read the original value, write the test value, rebuild, optionally pause for observation, restore by default, and do not save.
- Modify geometry: create a design record, state the hypothesis, then apply the smallest History mutation.
- Add/delete structures: specify target objects, materials, coordinate systems, boolean operations, and rollback strategy.
- Read results: discover result-tree paths before reading S-parameters, farfield, efficiency, gain, logs, or exported tables.
- Optimize or use ML: treat CST as the expensive ground-truth evaluator and record every trial input, output, project copy, log, and dataset version.

## Output Contract

When finishing a CST task, report:

```yaml
project_path: used or generated CST project
save_policy: no_save | save_copy | save_original
design_id: current structure version
parent_design_id: previous structure version or null
mcp_tools: MCP tools called during the task
operations: parameter/modeling/simulation/result-reading steps
metrics: extracted values with source paths
logs: Model.log/output.json/outputDS.json paths
artifacts: generated files, datasets, plots, manifests, model cards
versions: dataset_version, surrogate_version, CST project copy version
source_macros: CST installed macro paths used as references or adapted sources
warnings: assumptions, skipped steps, risks
errors: failures and recovery attempts
```
