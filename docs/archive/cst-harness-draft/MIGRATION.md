# Migration notes

This directory is a proposed content package, not a completed MCP implementation.
The JSON file defines a proposed configuration format; the current server does not
necessarily consume it. Do not advertise it as a working client configuration.

Source reviewed: the public `CST` branch of `jame-ri/cst2026-skill-mcp`, reached
through the user's original repository URL. Local workspace contents and the two
attached analyses were unavailable because local execution tools failed to start.

## Consolidate

- Replace the large skill entry with the short workflow and invariant contract.
- Put stage transitions, failure behavior, and completion rules in one harness
  document. Reference specialized electromagnetic checks rather than copying them.
- Keep bilingual onboarding concise and point both versions to the same canonical
  contracts. Avoid independently maintained copies of the same workflow.
- Replace static host-specific tool-name tables with capability discovery and
  optional explicit bindings. Preserve existing agent configuration examples.
- Remove cached machine paths from shared environment references. Keep external
  installation discovery in a local runtime binding.
- Keep the static cookbook as seed knowledge; runtime lessons require a separate
  writable store that the search implementation actually reads.

## Correct

- Search lessons before the first repair, not only after the same error repeats.
- Separate a failed occurrence, proposed fix, and verified reusable lesson.
- Do not equate planned inspection with executed evidence.
- Do not reuse a gate pass after changing its input model or configuration.
- Scope solver gates to requested work; modeling-only output can be delivered
  without pretending simulation happened.
- Preserve user authorization across stages and retries within its original scope.
- Treat source references as reusable versioned evidence rather than repeatedly
  loading unchanged documentation for every step.

## Implement in order

1. Introduce a shared configuration and path resolver used by all relevant tools.
2. Add transactional lesson persistence and integrate it with lesson retrieval.
3. Add a run store, state transitions, evidence invalidation, and retry budgets.
4. Route mutating operations through the harness and implement recovery reconciliation.
5. Adapt existing checkpoint/record tools without discarding old user records.
6. Run the acceptance cases in `HARNESS.md` using a fake CST adapter first; reserve
   actual CST execution for explicitly scoped integration checks.

After integration, place the skill and supporting documents together or regenerate
their relative links. Keep runtime data outside read-only installed skill packages.
