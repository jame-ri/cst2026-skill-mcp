---
name: cst-python-automation
description: Directly operate CST Studio Suite projects through session-bound APIs, read parameters and results, run authorized solvers, and extend a reusable API library through evidence-backed trials. Use for CST project automation, History/VBA and CST-specific simulation workflows, not general RF theory or unrelated plotting.
---

# CST API Harness

Use existing APIs first. This skill defines agent behavior; the implementation lives in the repository's CST API layer and is shared by different MCP clients.

## Main path

1. Identify the user's task, selected CST instance/project and existing authorization.
2. If the API ID is known, call it directly. Otherwise use `api.search` and `api.describe`.
3. Connect explicitly with `cst.connect`; bind an exact relative project path with `cst.open_project`.
4. Use the returned session/project/job IDs. Do not guess IDs, tree paths, parameter names or run IDs.
5. Perform the authorized operation, inspect actual evidence and report its limits.

Do not prepend documentation or vector searches to known operations. `api.call` and direct `cst.*` tools share one controller. Live reads also require `execute=true`; without it, tools return plans.

## Missing API: learn a reusable implementation

1. Confirm the capability is absent from the callable API catalog.
2. Consult the relevant official Python/History/VBA references, not broad unrelated files.
3. Write a parameterized Python entrypoint, separate postcondition verifier and versioned candidate JSON.
4. Stage the candidate with `api.stage`. Staging saves source, not proof of success.
5. Review the source and obtain authorization for local Python execution and any engineering changes. Do not silently enable extension execution.
6. Trial with `api.trial` against the selected project, preferably an authorized copy for experimental changes.
7. Reuse the exact registered `user.name@version` only after a passing verifier and durable receipt. Registration is automatic by default when those conditions hold.
8. On verification failure, preserve evidence. Retire or replace with a new version; never label unexecuted code as verified.

See [API development](../../../docs/api-development.md) for schema and example details. Python extensions are not sandboxed. The supplied verifier establishes only its checked local postconditions, not independent physics validity.

## Execution and safety

- Preserve prior authorization, but do not infer authorization to solve, stop, overwrite, create instances or run generated code.
- Read real parameters before changing them. Parameter expressions and evaluated values are different.
- Copying before modification is separate from recording a manifest. Neither a manifest nor an operation receipt is a project backup.
- Default saves use a different copy path. Saving the original, overwriting or closing needs explicit intent.
- `cst.run_solver` submits the configured solver and returns a job ID; poll status rather than blocking a tool for the whole simulation.
- `not_running` does not prove convergence or success. Check logs, expected results and run provenance.
- Do not assume stored results reflect the latest parameter changes. Report stale/unknown freshness and units as supplied by CST.
- A mutation may partially succeed. Unknown outcomes require state inspection, not automatic replay.
- Reuse an operation ID only to retrieve its existing receipt. Worker loss invalidates live IDs.
- Disconnect releases the session; it does not save, close CST or stop solvers.
- Avoid concurrent GUI/legacy/controller edits to the same project.
- Use repository-relative paths for projects, artifacts, candidates and local models. Resolve machine bindings at runtime; do not hardcode drive or user paths in reusable code.

## Electromagnetic scope

For modeling or solve decisions, apply only the relevant checks: units, material/geometry, feed/ports, boundaries, mesh, frequency range and monitors. Consult [EM gates](references/em-gates.md) when applicable.

Distinguish planned setup, implemented geometry, solver submission, successful computation, result freshness and physical validity. Do not add heavy simulation gates to a documentation-only or parameter-read task.

## References and delivery

- [Harness contract](references/harness.md): execution evidence versus auxiliary textual memory.
- [Architecture](../../../docs/architecture.md): API, MCP and runtime ownership.
- `official-docs/`, `macro-library/`, `domain-guides/`: targeted fallback sources when capability is missing.

Report what actually ran, returned identifiers, changed/saved files, verification evidence and unresolved limits. Do not claim tests, a solver run or API validation that was not performed.
