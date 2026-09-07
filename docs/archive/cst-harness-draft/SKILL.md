---
name: cst-automation
description: Use for CST Studio Suite project inspection, modeling, physics setup, simulation, result extraction, and recovery. Exclude general RF theory and unrelated plotting.
---

# CST automation

This is a proposed replacement entry point, not an installed runtime.
Read `HARNESS.md` for the execution contract and `config.example.json` for
configuration fields. The original repository is unchanged by this draft.

## Start

1. Resolve the active configuration and discover the available tool schemas.
2. Capture the objective, project reference, requested deliverables, acceptance
   criteria, and authorization already present in the conversation.
3. Inspect only the state needed for the next action. Retrieve relevant recipes
   and lessons before making changes or repairing failures.
4. Execute the applicable stages in `HARNESS.md`; checkpoint verified progress.
5. Deliver artifact references, validation evidence, and unresolved limitations.

## Invariants

- Use root-qualified relative references for projects, sources, and artifacts.
  Never put machine-specific absolute paths in instructions or shared records.
- Use the current agent's discovered callable names. Do not assume a provider
  prefix, a particular shell, or a tool that has not been discovered.
- Work on a project copy for mutations unless updating the original is authorized.
  Operate only on the identified project and helper-owned resources.
- Establish units and parameters before dependent History commands. Keep model
  changes visible in named, appropriately scoped History entries.
- Check structure, connectivity, materials, excitation, boundaries, and solver
  settings to the extent required by the requested task. Tree presence alone
  does not prove geometry contact or physical validity.
- A dry run, successful transport response, or populated result tree is not
  evidence that the intended CST operation succeeded.
- After a failure, inspect partial state, retrieve lessons, repair the smallest
  cause, and verify before recording a successful lesson. Bound retries.
- Reuse existing authorization. Ask only when consequential missing information
  or an action outside the authorized scope prevents progress.
- Load specialized references on demand. Do not preload the whole knowledge base.

## Reporting

State what was actually completed and provide relative artifact references.
Separate model construction, setup validation, solver execution, convergence,
and physical interpretation. Report unexecuted stages and remaining blockers.
