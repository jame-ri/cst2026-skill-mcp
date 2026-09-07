# Harness contract

The harness supports a direct API workflow. It is not a mandatory retrieval layer.

## Primary loop

```text
known API -> direct call -> actual outcome -> durable mutation/extension receipt
missing API -> references -> candidate -> reviewed trial -> postcondition evidence
            -> locally verified registration -> exact-ID reuse
```

The executable API library is implemented under `api_library/`. Its default data directory is `design-records/api-library/`. See [development instructions](../../../../docs/api-development.md) and [architecture](../../../../docs/architecture.md).

## Execution evidence

- `design-records/direct-operations/` holds intent and outcome records for journaled operations.
- Intent must be saved before dispatch. A post-execution recording failure must not cause another CST action.
- An operation ID binds the request. Identical retries retrieve the existing receipt; incomplete outcomes block replay.
- A passing extension verifier plus a durable receipt can register the exact candidate version.
- `locally_verified` is scoped to observed CST/version/inputs and the supplied verifier, not a general correctness guarantee.
- Candidate, disputed and retired implementations are not ordinary callable APIs.
- A simulation process stopping is not proof of successful or physically valid results.

## Secondary textual workflow memory

The retained `KnowledgeStore` records textual lessons, workflow observations and source-manifest evidence. It is distinct from executable API registration.

The legacy tools and automatic capture hooks are available through the `full` MCP profile. Textual memory may help explain a prior failure or an unfamiliar workflow; it must not be queried before every known API call.

Existing textual-memory controls remain `CST_KNOWLEDGE_ENABLED`, `CST_KNOWLEDGE_AUTO_CAPTURE`, `CST_KNOWLEDGE_DIR` and `CST_KNOWLEDGE_STABLE_RUNS`. Existing candidate/verified/stable/disputed labels describe those text observations, not permission to execute code.

Automatic capture still depends on the legacy record/checkpoint hooks. Manually run scripts do not gain capture or API registration merely because this skill mentions a harness.

## Authorization and limits

Extension execution requires both the operator environment gate and per-call consent. Arbitrary local Python has the server's privileges; neither metadata nor the verifier is a sandbox.

New APIs should use relative paths, explicit input contracts, bounded outputs and independent state re-observation. A repair uses a new version rather than silently replacing a registered source artifact.

Record and registration errors are secondary outcomes. Preserve the actual CST response and ask for the appropriate recovery action instead of repeating a possibly destructive step.
