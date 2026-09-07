# Runtime workflows

Load only the section needed for the current task. The entry skill defines scope
and authorization; [harness.md](harness.md) defines recording and memory.

## Sessions and project ownership

Inspect existing sessions/projects before cold start. Reuse the identified target
when suitable. A project mentioned in a manifest is not proof that it is open,
saved, or copied.

For helper-owned scratch projects, apply an explicit no-save or save-copy policy.
For artifacts, save to the authorized destination before closing. Resolve projects
before closing their owning DesignEnvironment using the documented API for the
installed CST version. Do not close unrelated user-owned projects.

Put helper-owned cleanup in finally blocks. Preserve the original failure if
cleanup also fails. Do not delete intermediate evidence needed for recovery.

An Update Manager license/update popup is an environment failure, not a geometry
error. Inspect process state and known lessons; do not repeat modeling commands
against a blocked dialog. Persistent update/license changes require task authority.
Terminate only identified stale PIDs with the cleanup tool's explicit controls.

## Long solves, sweeps and recovery

Before expensive work, check processes, available memory/disk, a bounded timeout,
target ownership, and requested trial count. An already authorized independent job
need not ask again merely because another process exists, but resource and project
conflicts must be resolved before proceeding.

Create a job record and checkpoint running before a fragile stage. Mark done only
after observing its postconditions. Mark failure or interruption honestly, keeping
earlier errors visible even if a later attempt succeeds.

On recovery, read the checkpoint, inspect the actual project, processes and outputs,
and reconcile an unknown outcome before deciding to resume. A missing completion
record does not prove an operation never ran. Never blindly replay geometry edits,
solver starts, saves, or cleanup.

Changing geometry, parameters, ports or solver settings invalidates affected prior
checks. Reinspect the changed state before using a prior result or gate pass.

## Results and engineering conclusions

Discover result-tree paths before extraction. Record project revision, run ID,
quantity, units, frequency range, excitation, reference impedance, normalization,
de-embedding and calibration plane when relevant. Keep saved and live results
distinct. An old tree can remain after a failed or unexecuted new solve.

Interpret sanity checks under their assumptions. For eligible passive,
power-normalized propagating port results, magnitude bounds may be useful;
they are not a universal proof for every modal normalization. Do not compare a
linear magnitude directly to a dB threshold: amplitude dB is 20 log10(magnitude).

For farfield results, check monitor frequency, gain versus realized gain versus
directivity, power/efficiency consistency, direction and polarization. For
plane-wave scattering, use the requested fields/RCS rather than assuming an
ordinary driven-port S-parameter result exists.

Check convergence, mesh/adaptation evidence and relevant warnings. Classify a
warning by its impact on the requested result; do not treat all warnings as either
harmless or universally blocking. Unchecked output remains unvalidated data.

## Physics-guided tuning and datasets

State a physical mechanism hypothesis, choose plausible sensitive parameters,
and prefer bounded one-at-a-time or low-dimensional probes before larger searches.
Use the observed response to build a parameter_mode_map and refine the step size.

Record the varied values, fixed values, project copy/version, frequency response,
matching, gain/efficiency or field evidence as relevant, and physical interpretation.
A better S11 alone does not establish a better antenna if other required metrics
degrade. Report the tradeoff.

Optimizers and surrogate models propose candidates; CST and verification supply
the task's evidence. Record each trial, failed trials, input/output units, dataset
version and model version. Separate measured results from predicted values.

Reusable inspection, parameterization, port setup, bounded scan and extraction
sequences may be captured through operation.knowledge. Parameterize local names
and dimensions; preserve applicability, preconditions and verification artifacts.
Do not generalize a single antenna's dimensions or tuned values into a universal rule.
