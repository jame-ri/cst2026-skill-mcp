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
6. If MCP is unavailable, read repository references directly and write Python/VBA/History scripts under the same safety rules.

## Reference Priority

Read these sources as needed:

1. `D:\CSTapi\mcp\README.md`
2. `D:\CSTapi\official-docs\python\`
3. `D:\CSTapi\official-docs\python_cst_libraries\cst\`
4. `D:\CSTapi\official-docs\vba-3d\`
5. `D:\CSTapi\official-docs\vba-des\`
6. `D:\CSTapi\official-docs\advanced\`
7. `D:\CSTapi\macro-library\macro-inventory.csv`
8. `D:\CSTapi\macro-library\cst-macro-usage.en.md`
9. `D:\CSTapi\macro-library\macro-catalog.en.md`
10. `D:\CSTapi\domain-guides\design-evolution.en.md`
11. `D:\CSTapi\domain-guides\geometry-mutation.en.md`
12. `D:\CSTapi\domain-guides\result-diagnosis.en.md`
13. `D:\CSTapi\domain-guides\optimization-ml-data.en.md`

## Operating Rules

1. Inspect the current project, parameters, result tree, or existing record before proposing changes.
2. Prefer official CST references, installed macros, and repository examples over guesswork.
3. Use `cst.interface` for live sessions and `cst.results` for saved result reads.
4. Use `model3d.add_to_history()` for geometry, ports, boundaries, mesh, and solver setup.
5. If a CST VBA/History command is unfamiliar, search the macro library and extract the smallest controllable snippet instead of batch-running full interactive macros as black boxes.
6. Do not save the original project by default; destructive edits, structure deletion, long simulations, and optimization loops should use a copied project or job copy.
7. Complex structure evolution must record `design_id`, `parent_design_id`, operations, metrics, logs, dataset versions, and surrogate versions.
8. Only use APIs, method names, and parameter names confirmed in official docs, installed macros, or repository code.
9. If an API detail is uncertain, verify it first instead of filling the gap with assumptions.

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
