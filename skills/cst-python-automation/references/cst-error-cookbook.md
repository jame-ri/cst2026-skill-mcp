# CST Error Cookbook

Use this file when a CST automation call fails, stalls, produces a modal dialog,
or makes the agent rediscover a working pattern. Add new lessons whenever a
failure is diagnosed and corrected.

## lesson: update-manager-license-popup

Symptoms:

- CST startup shows `License details are required to check for updates`.
- Automation appears to hang before modeling commands run.

Root cause:

- CST Update Manager is trying to check for updates and opens a modal license
  configuration dialog.

Correct response:

- Do not debug geometry or ports as if they failed.
- Run `cst.process_status` or `cst.preflight_resources` and report the modal
  risk.
- Ask the user to disable automatic software updates in CST Preferences or
  repair Update Manager license settings.

Next time:

- Check process/resource preflight before starting CST.

## lesson: save-prompt-untitled-project

Symptoms:

- CST asks whether to save changes to `Untitled_*.cst`.
- A helper script creates additional Untitled projects and then stalls.
- `DesignEnvironment.close()` does not resolve the intended save behavior.

Root cause:

- A helper called `new_mws()` or created a temporary project without applying an
  explicit project save/close policy first.

Correct response:

- In helper-owned scratch projects, call `Project.close()` for `no_save`.
- For artifacts, call `Project.save(copy_path, include_results,
  allow_overwrite)` and then `Project.close()`.
- Only after helper-owned projects are closed may the script call
  `DesignEnvironment.close()`.

Next time:

- Use `cst.close_project` with explicit `save_policy`.
- Put close policy in `finally` blocks for scripts that create new projects.

## lesson: active-solver-process-conflict

Symptoms:

- A new build or solve is requested while existing CST modeler/solver processes
  are running.
- Previous records mention active solver PIDs and no solver was started.

Root cause:

- Launching another long CST job can collide with an active solve, consume
  memory, or produce ambiguous project ownership.

Correct response:

- Run `cst.process_status` or `cst.preflight_resources`.
- Record an `interrupted` checkpoint if it is unsafe to proceed.
- Reuse an open session only when the target project is clear.
- Do not terminate processes without explicit PIDs and `allow_terminate=true`.

Next time:

- Treat preflight as mandatory before long solves, sweeps, and optimization.

## lesson: command-line-encoding-chinese-path

Symptoms:

- Process listing with command lines fails or returns encoding errors on paths
  containing Chinese characters.
- A previous checkpoint mentioned a GBK encoding issue during process-status.

Root cause:

- Windows process command-line output can include non-UTF-8 text that breaks
  JSON or shell decoding.

Correct response:

- Retry process status without command lines when path text is not needed.
- Use PowerShell process listing as a fallback for PID/name/working-set
  confirmation.
- Keep project paths in JSON records, but do not rely on command-line decoding
  for correctness.

Next time:

- Prefer `include_commandline=false` when command-line detail is unnecessary.

## lesson: tree-inspection-cannot-prove-face-contact

Symptoms:

- `cst.inspect_geometry` or `cst.inspect_physics_setup` finds objects and ports,
  but exact face IDs, contacts, overlaps, or clearances remain uncertain.
- Review records warn that visual GUI inspection is still required.

Root cause:

- The current helper uses accessible tree evidence; it cannot fully prove
  geometric contact, exact bounding boxes, face picks, or conductor continuity.

Correct response:

- Report this as an explicit review risk.
- Stop at the review gate before solver execution when topology depends on the
  uncertain contact/face.
- Prefer future structure extraction helpers that compute bounding boxes,
  contacts, and Boolean lineage.

Next time:

- Do not claim physical validity from tree presence alone.

## lesson: distributed-feed-replaced-by-discrete-port

Symptoms:

- A microstrip, coax, SIW, or waveguide feed is modeled with `DiscretePort`
  because waveguide `Port` setup was harder.
- Results shift unexpectedly or no longer represent the intended distributed
  feed.

Root cause:

- The port object was chosen for convenience instead of physical feed type.

Correct response:

- For distributed line feeds, create a physical cross-section and use waveguide
  `Port`.
- Search macros for `Port`, `Port Mode`, and `Calculate port extension
  coefficient`.
- Use picked-face workflow or explicit free-coordinate port aperture only after
  confirming the CST pattern.

Next time:

- Do not silently downgrade waveguide/coax/SIW/microstrip ports to
  `DiscretePort`.

## lesson: parameter-used-before-store

Symptoms:

- History rebuild prompts for undefined parameters or stalls in CST.
- A History command references a parameter name not yet in the CST parameter
  table.

Root cause:

- `StoreParameter` or `StoreParameterWithDescription` was not called before
  geometry, materials, ports, or solver History referenced the parameter.

Correct response:

- Reorder History: units first, parameters next, then frequency, materials,
  geometry, ports, mesh, monitors, and solver setup.
- Rebuild after repairing the order.

Next time:

- Generate parameter definitions before every parameterized History block.

## lesson: history-not-visible-or-too-collapsed

Symptoms:

- Generated geometry exists, but the CST GUI History tree lacks readable entries.
- Many unrelated operations appear under one broad caption.

Root cause:

- Geometry was created through direct helper side effects or overly broad
  `add_to_history` blocks instead of visible, inspectable History entries.

Correct response:

- Rebuild with one physical object or one tightly coupled operation per History
  caption.
- Verify persisted History after saving, preferably by checking
  `Model/3D/ModelHistory.json` or an available CST inspection tool.

Next time:

- Treat History tree readability as a deliverable.
