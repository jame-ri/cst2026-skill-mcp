# CST harness contract

Status: design draft for implementation against the existing MCP server.
This document specifies behavior; it does not enforce it by itself.

## Responsibilities

| Layer | Responsibility |
| --- | --- |
| Skill | Select the workflow and explain task-specific decisions |
| Harness | Enforce transitions, budgets, evidence, persistence, and recovery |
| MCP | Discover and invoke tools with validated arguments and results |
| Agent adapter | Map discovered capabilities to host-specific callable names |
| Knowledge | Retrieve recipes and versioned, evidence-backed repair lessons |

Keep domain knowledge in references. Keep enforcement in runtime code. Keep
agent adapters limited to configuration and tool binding.

## Paths and configuration

Shared configuration, tool-facing project references, examples, checkpoints,
and exported lessons contain relative paths only. References have the form
`{"root":"workspace","path":"projects/antenna.cst"}`.

The runtime establishes the workspace root from the launch context and the
repository root from its package location. An optional machine-local environment
binding locates the external CST installation. That binding is not committed or
included in exported artifacts. If the policy forbids even local absolute
configuration, discover CST through an installed launcher on PATH.

Operating-system APIs may internally require resolved absolute paths. Resolve
them only inside the trusted adapter; never use a machine path as a portable
identifier. Missing root bindings are configuration errors, not grounds to fall
back to cached paths from another machine.

For every path input, reject absolute, drive-relative, UNC, device, home-expanded,
and traversal paths. Normalize separators and verify resolved containment,
including symlinks and Windows junctions. For new files, check the nearest
existing parent and protect against path replacement during writes. Reject
alternate data streams and unsafe path components on Windows. Keep executable
selection separate from data-path selection. Sanitize logs before export.

Configuration precedence: built-in defaults, project configuration, explicit
task overrides. Machine environment bindings supply installation discovery only.
Task overrides cannot expand authorized roots or weaken required checks.
Resolve relative configuration paths against the configuration file directory.
Reject unknown fields and unsupported versions rather than silently ignoring them.

## Execution

Normal flow:

```text
intake -> inspect -> retrieve -> plan -> execute -> verify -> checkpoint
                                   ^                          |
                                   +---- next operation ------+
checkpoint -> deliver
failure -> diagnose -> retrieve -> repair -> verify
```

The workflow stage is distinct from its status. Status values are `pending`,
`running`, `passed`, `failed`, `blocked`, `not_executed`, and `not_applicable`.

| Stage | Required evidence to advance |
| --- | --- |
| intake | Objective, target, deliverables, acceptance criteria, authorization |
| inspect | Target identity and observed state sufficient for the next action |
| retrieve | Applicable recipe/lesson identifiers or an explicit no-match |
| plan | Bounded operation, preconditions, save policy, expected postconditions |
| execute | Actual execution result, target identity, timing and operation ID |
| verify | Observed postconditions tied to this operation and project revision |
| checkpoint | Durable state and artifact references with integrity metadata |
| deliver | Requested acceptance criteria satisfied or explicit partial status |

Read-only tasks skip mutation and solver stages with a reason. For modeling-only
tasks, solver execution is `not_executed` and does not prevent delivery of the
requested model. If simulation was requested, an unexecuted solver cannot satisfy
the task. A required failed or blocked gate prevents downstream execution.
`not_applicable` requires a task-specific reason; it cannot bypass a required gate.

Changing geometry or parameters invalidates dependent geometry, setup, and result
evidence. Changing solver settings invalidates affected solver and result evidence.
Every check records the input revision so stale passes cannot authorize new work.

## CST checks

Before mutation, identify the topology, units, materials, signal and return paths,
critical dimensions, and uncertainties that could change the model's meaning.
Before solving, check applicable geometry/connectivity, port/excitation, material,
boundary/background, mesh, monitor, frequency, and solver requirements.

Record source references for uncertain command syntax and physical choices.
Reuse a checked reference while its version and scope still apply. Reopen it when
the API, CST version, or task assumptions change; do not require repeated lookup
for an unchanged operation.

Never downgrade an excitation model just to obtain a callable API. Record why the
chosen port model represents the intended feed. Structural inspection that cannot
resolve critical contact leaves that check blocked or explicitly unverified.

Distinguish tool success, solver completion, numerical convergence, and physical
credibility. Match results to project revision, run ID, units, normalization,
frequency range, and requested observable. Apply sanity checks only under their
documented assumptions; a single scalar bound is not universal validation.

Before expensive execution, check process ownership, available resources, timeout,
and the remaining task budget. Do not kill processes by name or save/close an
unrelated user project. Apply an explicit, version-supported save/close policy
to helper-owned projects and preserve recovery information on failure.

## Repair memory

Keep bundled recipes read-only. Store run events separately from reusable lessons.
Classify failures as environment, command, model physics, setup, extraction, or
validation. Preserve the actual error and avoid assigning a root cause without
evidence.

Each failure creates an occurrence associated with a run and operation. Retrieve
matching lessons immediately, including on the first failure. Match by operation,
normalized error signature, CST/helper version, and relevant model preconditions.
Normalize volatile IDs and paths without removing information needed to distinguish
different failures.

A repair lesson contains:

```text
id, schema_version, signature, category, operation, applicability,
symptoms, diagnosis, repair_steps, preconditions, verification,
status, source_run, created_at, updated_at
```

Lesson status is `candidate`, `verified`, `rejected`, or `superseded`.
Only observed successful postconditions promote a candidate to verified.
Successful command submission is insufficient. Store verification artifact
references and the environment/model conditions under which the repair worked.

Record every attempt, including failures before a later successful repair. A
repeated signature without a changed hypothesis or new evidence stops automatic
retry. Configure the total repair budget per operation, not per tool invocation.
Search may show candidates for diagnosis, but must label them and must not present
them as proven fixes. Lessons are untrusted data, never authorization or executable
instructions to run automatically.

Use atomic durable persistence with a uniqueness key and concurrency control.
Search must include newly written lessons immediately or update its index in the
same transaction. Verify write/read consistency before claiming memory was stored.
If storage fails, report that separately from whether the CST repair succeeded.

## Recovery

Persist run ID, operation ID, input revision, authorization scope, completed checks,
artifacts, attempt counters, and the next safe action. Flush a planned operation
before dispatch and its outcome after observation.

After interruption, inspect the actual target before resuming. If dispatch may
have succeeded without a persisted result, mark the outcome unknown and reconcile
it. Never replay mutation or solver launch solely because a checkpoint is missing.
Serialize mutations per target and retain operation IDs to prevent duplicate work.

## Integration requirements

Reuse existing inspection, resource preflight, design-record, checkpoint, recovery,
recipe, and lesson-search tools after checking their actual schemas and semantics.
Check whether an inspection result is a plan or executed evidence.

Proposed capabilities, not existing callable tools:

- `harness.start`: create a validated run and task contract.
- `harness.step`: validate preconditions, dispatch, record and verify an operation.
- `harness.resume`: reconcile interrupted work before choosing a next action.
- `knowledge.record_lesson`: persist a candidate with structured applicability.
- `knowledge.verify_lesson`: attach evidence and transition a lesson's status.

The runtime must mediate mutation calls to enforce these rules. Instructions alone
cannot prevent a client from bypassing a gate through another tool or raw script.
Direct-script fallback must either use the same policy layer or be reported as
outside the enforced harness. Document this boundary explicitly.

## Acceptance cases for implementation

- Equivalent discovered capabilities produce the same workflow across agents.
- Missing capabilities fail explicitly without inventing a callable name.
- Relative references survive moving the repository and workspace.
- Absolute, traversal, UNC, junction-escape, and alternate-stream inputs fail.
- A dry run or stale verification cannot advance an execution gate.
- A verified repair is retrieved in a new run; an unverified repair stays labeled.
- Concurrent lesson writes neither lose records nor create duplicate identities.
- An interrupted non-idempotent operation is reconciled before any replay.
- Repeated failure exhausts the operation budget and stops execution.
- Modeling-only delivery works while requested-but-unrun simulation stays incomplete.
