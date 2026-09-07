# README Repository Overview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the API-centric root README with a bilingual overview of the complete CST 2026 Skill + MCP repository.

**Architecture:** Keep the root README focused on product purpose, repository components, setup, ordinary operation, and safety. Link specialized API-extension and internal architecture details to existing documents instead of reproducing them.

**Tech Stack:** Markdown, MCP configuration examples, Node.js stdio server, CST Python integration.

## Global Constraints

- Modify only `README.md`; the design and plan documents describe the change.
- Preserve complete Chinese and English coverage.
- Use `CST 2026 Skill + MCP` as the repository identity.
- Treat API extension, Harness memory, and vector discovery as optional advanced capabilities.
- Do not claim live CST validation or test execution that did not occur.
- Use only repository-relative paths in configuration and operation examples.

---

### Task 1: Rewrite the repository README

**Files:**

- Modify: `README.md`

**Interfaces:**

- Consumes: current repository layout, `config/mcp-client.example.json`, `config/codex.example.toml`, `mcp/README.md`, `docs/architecture.md`, and `docs/api-development.md`.
- Produces: a bilingual landing page that routes readers to the appropriate detailed document.

- [ ] **Step 1: Replace the title and opening**

Use `# CST 2026 Skill + MCP` and explain that the repository combines agent instructions, an MCP server, CST execution, safety records, and reference material.

- [ ] **Step 2: Introduce capabilities and component relationships**

List connection, project, parameter, solver, result, recovery, and optional extension capabilities. Explain Skill, MCP, CST API, Harness, and references without making the internal API library the product title.

- [ ] **Step 3: Document the repository structure**

Provide a table covering `skills/`, `mcp/`, `cst_api/`, `harness/`, `api_library/`, `shared/`, `config/`, `docs/`, the reference collections, and `design-records/`.

- [ ] **Step 4: Document setup for multiple agents**

Describe Node.js and CST requirements, the generic and Codex configuration files, Claude-compatible MCP configuration, launch scripts, working-directory requirements, and skill loading.

- [ ] **Step 5: Document the ordinary CST workflow**

Explain connect, bind project, inspect, copy/save, modify, solve with authorization, poll, read results, save, and disconnect. Keep actual returned identifiers and plan-only defaults explicit.

- [ ] **Step 6: Summarize tools and optional facilities**

Group the default tools by user task. Summarize `full` profile compatibility tools and the missing-API learning loop in short sections, linking details to existing documents.

- [ ] **Step 7: Preserve safety and limitation statements**

Retain relative-path rules, explicit execution gates, unknown-outcome handling, result-validity distinctions, extension security warning, cooperative CST ownership, and the current lack of new live-CST validation.

- [ ] **Step 8: Verify Markdown and commit**

Run:

```powershell
git diff --check -- README.md
```

Expected: no whitespace errors.

Run:

```powershell
git add README.md
git commit -m "docs: refocus README on CST Skill and MCP"
```

Expected: one documentation commit containing the README rewrite.
