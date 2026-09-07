# CST direct-control MCP with auxiliary template retrieval

Status: proposed implementation design; the operating direction is user-approved.
This document is not a claim that these interfaces are implemented.

## Goal

Make direct CST connection and operation the primary MCP workflow. Known actions
call registered, parameterized templates directly. Vector retrieval helps find
templates only when the caller does not know a suitable template ID.
Neither documentation lookup nor vector search is a mandatory execution step.

## Architecture decision

Use a persistent Python worker owned by each MCP server process. It holds CST
connection/project objects and serves bounded JSON requests from the Node server.
Node owns public schemas, session IDs, request correlation, execution policy,
timeouts, operation records, and template discovery.

This is preferable to repeated implicit connect-to-any calls because it makes
instance/project identity explicit across sequential operations. Explicit PID
reconnection per call remains a possible compatibility backend, not a silent
fallback. A documentation/retrieval-first router is rejected for this use case.

Direct-control, retrieval, and long solver tasks are separate implementation
stages. A working direct-control stage must not depend on an embedding model.

## Stage 1: direct connection and known operations

Proposed public interfaces:

| Tool | Responsibility |
| --- | --- |
| cst.connect | Attach to an explicit CST instance, or create one only with explicit create intent |
| cst.session_status | Report connection health, ownership, bound project and capability availability |
| cst.disconnect | Release the MCP session without saving or closing user projects/CST |
| cst.list_projects | List projects in the bound instance |
| cst.open_project | Bind an already-open project or open an explicitly requested repository-relative project |
| cst.run_template | Invoke a registered template ID with schema-validated parameters |
| templates.list | List available templates and capabilities without semantic search |
| templates.get | Read one template's schema, effects, applicability and provenance |
| cst.doctor | Inspect configured runtime, import availability and storage settings without opening CST |

A successful connection returns an opaque session_id. Subsequent operations use
that session ID, not an inferred active window. When multiple CST instances exist,
never silently choose one. Existing user-owned instances are attached, not adopted
as helper-owned. Connect-only requests must never fall back to creating CST.

Each project receives an opaque project_id and a relative project reference when
inside the permitted repository. Out-of-root projects are not operable through
these APIs. Existing project IDs are rechecked before a mutation.

Initial templates cover project inspection, parameter read, parameter write with
optional rebuild, explicit rebuild, and save-copy without closing the project.
Available capabilities must be based on checked CST APIs, not guessed method names.
Unsupported methods return capability_unavailable rather than probing mutations.

A save-copy template reports that Save As may change the open project's filename;
it updates the bound project reference and does not pretend the original remains
the active project. Parameter writes report the prior value, requested value,
observed value when readable, and rebuild outcome. They do not claim atomic
rollback after an uncertain CST failure.

Use declarative template metadata and a fixed implementation registry. Parameters
are data, not source text passed to eval/exec. Arbitrary Python or History execution
is not introduced under the name of a generic template tool.

## Template contract

Each template has a stable ID, immutable version, implementation digest, argument
schema, description, effects, CST/API applicability, checked reference provenance,
postconditions, and verification status.

Bundled templates are reviewed source code. Newly learned scripts are stored as
candidates outside the executable registry. Capturing code or finding it with
vector search does not install, approve or execute it.

Known template IDs bypass retrieval entirely. If a template is incompatible,
disabled, missing, or unverified for the requested effect, fail explicitly rather
than selecting a similar script and running it.

## Execution policy and automatic records

CST execution remains explicit. Dry runs do not connect, create workers that
import CST, write success evidence, or execute templates. Read-only execution may
connect to CST and is distinct from a dry run.

Before a state-changing command, allocate an operation_id and durably record its
intent. If this write fails, do not dispatch the mutation. After dispatch, preserve
success, failure, interruption, timeout, or unknown-outcome status and evidence.
A post-execution record/capture failure must never trigger a repeat CST operation.

Reuse of an operation_id is bound to the identical command digest. Finished
requests return the recorded outcome; unfinished or uncertain mutations require
state inspection rather than replay. New IDs are not proof that replay is safe.

Automatic records include session/project identity, template ID/version/digest,
arguments, timestamps, result status and artifact references. Do not store CST
objects, credentials, or reusable machine-absolute paths. Records of successful
API calls are not independent proof of electromagnetic validity.

Only verified outcomes may become verified knowledge. Existing knowledge capture
and lifecycle rules remain applicable. Failure to capture knowledge is reported
separately from failure of the CST action.

Serialize state-changing commands for the same CST instance within the controller.
Use an owned local instance lease across controllers on the same host; its identity
must include a process-start marker where available to reduce PID reuse hazards.
Refuse conflicting control when ownership cannot be established. Do not silently
delete a stale lease or assume file-record locks protect CST itself.

## Worker lifecycle and failure behavior

Worker protocol uses request IDs, bounded messages, and a dedicated stdout channel.
Diagnostics go to stderr. CST handles stay inside their owning worker; do not pass
live handles across threads or JSON.

Worker EOF, crash, or timeout invalidates the session. Mutations in flight become
unknown-outcome until inspected. Restarting a worker does not auto-repeat them.
Stopping the worker does not imply CST or its solver stopped.

Disconnect is not save, close-project, or terminate-process. Destructive lifecycle
actions remain separately authorized. Do not close user-owned projects on MCP
shutdown. Explicit cleanup requires ownership information and an appropriate
save/close policy.

## Stage 2: auxiliary vector retrieval

Provide templates.search(query, filters, limit) to return candidate template IDs,
versions, applicability and provenance. Retrieval never executes a result.

Use a configurable local embedding provider and a local index initially. Do not
automatically download model weights, install dependencies, send scripts to a
remote service, or embed secrets. The operator supplies a compatible local model.
A future remote provider requires an explicit configuration and privacy decision.

Index template descriptions, tags, schemas and concise code summaries. Store full
script artifacts separately and associate them by ID/version/digest. Do not treat
a vector index as the authoritative script store.

Persist embedding provider/model revision, dimension, normalization and template
digest with the index. Reject incompatible indexes and require explicit rebuild.
Exclude unapproved/retired templates from executable recommendations. CST/API
compatibility filtering occurs before a candidate can be selected for execution.

When embeddings are unavailable, report vector_unavailable. An explicit keyword
fallback may return results labeled keyword, never labeled vector or semantic.
Known-ID execution must remain available regardless of index/model status.

Retirement and replacement metadata are explicit, append-only lifecycle events.
A candidate script is not automatically promoted because it resembles a stable
template.

## Stage 3: solver jobs and result export

After the connection and template foundation is accepted, add solver start,
status, cancellation and run-specific result export as a separate task lifecycle.
Record actual project version, parameter snapshot and run identity.

Long solves must not block status/cancellation transport. Choose the CST-supported
execution/control mechanism after checking the installed API; do not assume a
blocking solver method is safely callable from arbitrary worker threads.
Cancellation must report whether it was requested or confirmed.

A solver start requires user authorization plus applicable setup/resource gates.
Results from a previous run are not evidence for the current one. Export includes
units, axes, complex-value conventions, selected tree path and run identity.
No solver tool is advertised as working merely because a checkpoint was written.

## Skill and compatibility changes

Update the repository skill's routing rules:

1. Use a matching known direct tool/template immediately.
2. Inspect state and enforce operation-specific authorization/preconditions.
3. Retrieve templates only when no suitable ID is known.
4. Consult official references only to implement an unfamiliar capability or
   resolve an incompatible/failed template.
5. Record source provenance when authoring templates, not repeated source lookup
   before every execution.

Preserve existing docs.*, knowledge.* and records.* interfaces for compatibility.
Label old short-lived helpers as legacy rather than removing them immediately.
Do not silently reroute old helpers to a different CST instance.

The currently installed skill copy still contains older lookup-first rules.
Updating repository files alone does not update that copy. Installation updates
must be deliberate, preserve local configuration, and avoid duplicate skill names.

Keep shared configuration agent-neutral. Runtime installation bindings live in the
local environment. Public filesystem arguments, template references, evidence and
store locations use contained relative paths.

## Planned file boundaries

- mcp/src/cst-controller.js: public tools, sessions, command dispatch and policy.
- mcp/src/cst-worker-client.js: worker transport, request lifecycle and timeouts.
- mcp/python/cst_worker.py: owned CST handles and documented CST calls.
- mcp/src/template-registry.js: schema/version/trust metadata and known-ID routing.
- mcp/templates/: reviewed metadata and fixed template implementation references.
- mcp/src/operation-journal.js: intent/outcome persistence and replay protection.
- mcp/src/template-search.js: auxiliary retrieval and index lifecycle.
- mcp/python/template_embeddings.py: optional local embedding adapter.
- mcp/src/server.js: register controller/retrieval tools without duplicating policy.
- skills/cst-python-automation/SKILL.md: direct-operation-first routing.
- README.md and mcp/README.md: bilingual setup, workflow and capability limits.

## Acceptance boundaries

Planned checks, to run only with user authorization:

- Mock worker tests for session identity, attach-only behavior, ownership,
  serialization, unknown outcomes, disconnect and rejected argument types.
- Template tests for known-ID execution without retrieval and rejected untrusted,
  incompatible or modified implementations.
- Journal tests for durable intent, matching-ID deduplication and no mutation
  replay after post-execution storage failure.
- Retrieval tests for model/dimension mismatch, offline status, explicit keyword
  fallback and exclusion of candidate/retired templates.
- Regression checks for existing tools and relative-path policy.
- Separately authorized live CST acceptance on a disposable project copy.

No real CST execution, dependency installation, model download, commit or push is
authorized merely by this design document. Static/mocked checks do not establish
that a real installed CST interface works.
