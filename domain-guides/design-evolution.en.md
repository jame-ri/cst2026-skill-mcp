# Complex Antenna Design Evolution Guide

## Purpose

Use this guide when antenna work is an evolving structure-design process rather than a simple antenna-template task. The agent should inspect the current CST project, diagnose metrics, propose a structural mutation, modify geometry in a copied project, simulate or read results, and record the next design version.

## Core Principles

- Do not assume the antenna type first. Inspect the CST project tree, components, materials, ports, boundaries, monitors, parameters, and existing results.
- Treat every design as a version: `parent_design_id -> mutation_id -> child_design_id`.
- Every mutation must state a hypothesis: what changes, why it changes, which metric it should improve, and what tradeoff it may introduce.
- Modify job copies by default; do not save the original project.
- Prefer small mutations for complex structures; avoid changing many coupled mechanisms at once.
- If geometry meaning is unclear, summarize the discovered structure and propose low-risk candidate edits.

## Version Naming

Recommended layout:

```text
runs/
  antenna-task-YYYYMMDD-HHMMSS/
    manifest.json
    trials.jsonl
    designs/
      D0000_baseline/
        project.cst
        design.json
        metrics.json
      D0001_add_slot_near_feed/
        project.cst
        design.json
        metrics.json
```

Recommended IDs:

- `task_id`: global ID for one user task or optimization run.
- `design_id`: `D0000`, `D0001`, `D0002`.
- `parent_design_id`: source design; baseline uses `null`.
- `mutation_id`: `M0001_add_slot_near_feed`.
- `project_version`: CST project version, usually matching `design_id`.
- `data_version`: dataset version, for example `dataset_v003`.
- `surrogate_version`: surrogate model version, for example `surrogate_v002`.

## Per-Design Record

Each `design.json` should include at least:

```json
{
  "task_id": "antenna-task-20260602-153000",
  "design_id": "D0001",
  "parent_design_id": "D0000",
  "mutation_id": "M0001_add_slot_near_feed",
  "project_path": "runs/.../designs/D0001_add_slot_near_feed/project.cst",
  "save_policy": "save_copy",
  "hypothesis": "Add a narrow slot near the feed to lengthen the current path and move resonance lower.",
  "operations": [
    {
      "type": "add_geometry",
      "target": "metal:slot_feed_1",
      "method": "history_vba_boolean_subtract",
      "parameters": {"slot_l": "8 mm", "slot_w": "0.6 mm"}
    }
  ],
  "expected_effects": ["S11 resonance moves lower", "matching improves near target band"],
  "risks": ["radiation efficiency may drop", "fabrication tolerance becomes tighter"],
  "created_at": "ISO-8601"
}
```

Each `trials.jsonl` row should include at least:

```json
{
  "trial_id": "T0001",
  "design_id": "D0001",
  "parent_design_id": "D0000",
  "project_path": "runs/.../D0001_add_slot_near_feed/project.cst",
  "parameters": {"slot_l": 8.0, "slot_w": 0.6},
  "metrics": {"s11_min_db": -18.2, "bandwidth_10db_ghz": 0.42, "gain_dbi": 4.8},
  "metric_sources": {"s11": "cst.results tree path ...", "gain": "farfield monitor ..."},
  "status": "completed",
  "logs": ["Result/Model.log"],
  "errors": []
}
```

## Evolution Workflow

1. Inspect the baseline project: path, parameters, structure tree, ports, materials, boundaries, monitors, and existing results.
2. Create `D0000_baseline`; store baseline metrics and a structure summary.
3. Diagnose the main issue: matching, bandwidth, gain, efficiency, pattern, polarization, size, or manufacturing constraints.
4. Choose the smallest effective mutation, such as feed, coupling, parasitic loading, slotting, ground, lumped loading, or array spacing.
5. Apply the History/VBA mutation in a project copy.
6. Rebuild and record geometry-edit logs.
7. Simulate or read existing results.
8. Write `metrics.json` and append `trials.jsonl`.
9. Decide the next step: refine, roll back, combine successful mutations, enter parameter optimization, or train a surrogate.

## Mutation Categories

- Feed mutations: feed position, feedline width, feed gap, probe location, coupled-feed distance, matching stubs.
- Current-path mutations: slots, meanders, branches, loading stubs, shorting pins, shorting plates, vias.
- Coupling mutations: parasitic elements, coupling slots, stacked patches, metasurface cells, loading rings.
- Ground mutations: ground length, defected ground structures, ground slots, chamfers, local ground edits.
- Radiator mutations: edge cuts, notches, local widening/narrowing, multi-branch shapes, tapered shapes.
- Array mutations: element spacing, feed phase, amplitude tapering, decoupling structures, array boundaries.
- Material/stackup mutations: substrate thickness, permittivity, loss tangent, air layer, metal thickness.

## When To Use Optimization Or Surrogates

- A structural mechanism works, but its parameter space is large.
- The goal is a multi-objective tradeoff among bandwidth, gain, size, and efficiency.
- Simulations are expensive and a surrogate can reduce CST calls.
- There are at least tens to hundreds of high-quality trials with consistent parameter and metric records.

## Output Requirements

Every round must report:

- `design_id` and `parent_design_id`.
- Structural mutation summary.
- CST project-copy path.
- Mutation hypothesis and expected effects.
- Actual metrics and metric sources.
- Whether the mutation is accepted for the next round.
- Data record paths: `design.json`, `metrics.json`, `trials.jsonl`.
