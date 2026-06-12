# CST Geometry Mutation Guide

## Purpose

Use this guide to safely add, remove, replace, subtract, or parameterize CST geometry in complex antenna projects. Geometry mutations must be traceable, recoverable, and reproducible.

## Pre-Edit Inspection

Before any structural mutation, record:

- Project path and whether it is a copy.
- Component list, solid names, sheet names, materials, and units.
- Parameter table and parameters related to the target structure.
- Ports, boundaries, monitors, and mesh settings.
- Protected structures such as feeds, reference ground, connectors, package geometry, and air box.

Do not delete objects whose role is unclear. Hide, copy, rename, or test in a copy first.

## Naming

Recommended names:

- New structure: `mut_M0003_slot_feed_1`, `mut_M0004_parasitic_arm_L`.
- Backup of replaced object: `bak_M0003_original_patch`.
- Temporary Boolean tool: `tool_M0003_slot_cut`.
- Component: `mutations/M0003` or `design/D0003`.

Names must include the mutation ID so CST tree objects can be mapped back to record files.

## Safe Mutation Strategy

- Add geometry: prefer creating new objects while leaving baseline geometry untouched.
- Delete geometry: prefer copied projects; if needed, rename originals to `bak_*` before deletion.
- Slot or cut: create a `tool_*` body, then Boolean subtract; record tool dimensions and target objects.
- Replace geometry: keep an original backup, create the new object, and verify ports/materials/boundaries.
- Batch changes: split into several mutations; do not mix multiple physical mechanisms in one History entry.
- Rebuild failure: record the failed History caption, roll back to the parent design, and do not stack further changes.

## History/VBA Record

Recommended `add_to_history()` caption:

```text
M0003 D0002->D0003 add slot near feed
```

Record each operation:

```json
{
  "mutation_id": "M0003",
  "history_caption": "M0003 D0002->D0003 add slot near feed",
  "operation": "boolean_subtract",
  "target_objects": ["metal:patch"],
  "tool_objects": ["tool_M0003_slot_cut"],
  "created_objects": ["mut_M0003_slot_feed_1"],
  "deleted_or_hidden_objects": [],
  "parameters": {"slot_l": "8 mm", "slot_w": "0.6 mm"},
  "rebuild_status": "completed"
}
```

## Common Geometry Actions

### Add Slots

Purpose: lengthen current paths, introduce resonances, tune matching, or alter polarization.

Notes:

- Slots near strong-current regions are usually effective but may reduce efficiency.
- Very narrow slots add manufacturing risk.
- Align slot location and orientation with the target current path; do not cut randomly.

### Add Parasitic Structures

Purpose: widen bandwidth, add coupled resonances, improve pattern, or improve gain.

Notes:

- Record spacing between the parasitic element and the main radiator.
- Parameterize distance, length, and width first.
- Watch efficiency and sidelobe changes.

### Modify Feed Structure

Purpose: improve input matching, impedance transformation, and bandwidth.

Notes:

- Record port definition and reference impedance before feed edits.
- Change feedline width, feed position, gap, or matching stubs one main factor at a time.
- Verify the port is still connected to the correct conductors.

### Modify Ground

Purpose: tune resonance, alter pattern, improve isolation, or reduce size.

Notes:

- Ground slots may increase back radiation or reduce efficiency.
- Miniaturization usually trades off bandwidth or efficiency.
- In arrays or multi-port designs, ground edits affect isolation.

### Add Shorting Pins Or Vias

Purpose: miniaturize, introduce modes, alter polarization, or tune matching.

Notes:

- Specify which objects or layers are shorted.
- Check metal continuity and mesh quality.
- Record via radius, position, and count.

## Rollback Rules

- If rebuild fails, keep the failure record and return to `parent_design_id`.
- If simulation fails after a successful rebuild, keep the design as `failed_simulation` but do not use it for the next optimization step.
- If metrics become clearly worse, mark the design `rejected` but keep the data; negative samples are useful for surrogates.
- If edits break ports or boundaries, roll back instead of continuing to patch an invalid structure.

## Output Requirements

After geometry mutation, report:

- Modified objects and new object names.
- History caption used.
- Parameters and units.
- Rebuild status.
- Whether a copy was saved.
- Structure-version record paths.
- Rollback or failure handling.
