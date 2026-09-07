# CST automation: English guide

Use [the canonical skill](cst-python-automation/SKILL.md). Install the
cst-python-automation directory as a unit so its relative references remain valid.
This page is an onboarding pointer, not a second independently maintained skill.

- The skill selects the task scope and preserves existing user authorization.
- The [harness](cst-python-automation/references/harness.md) connects execution
  records to automatically captured workflows and repair lessons.
- The [EM gates](cst-python-automation/references/em-design-gates.md) define
  model/setup checks; read-only questions do not require a full modeling ledger.
- The [environment reference](cst-python-automation/references/local-environment.md)
  covers portable paths and configuration for different agent hosts.

Connect the agent to this repository's MCP server and discover its actual tools.
Restart the server after code or environment changes. Different agents sharing
the same repository and knowledge configuration share learned entries.

Describe reusable steps in an operation/checkpoint. Check its returned capture
status; an unverified attempt is a candidate, not a proven workflow.
Existing records can be imported with knowledge.capture_operation.
