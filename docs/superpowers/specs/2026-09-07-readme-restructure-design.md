# README Repository Overview Design

## Goal

Rewrite the root README so it introduces the complete CST 2026 Skill + MCP repository instead of presenting the internal API-learning harness as the product.

## Audience

- CST users who want an agent to connect to and operate CST Studio Suite.
- Codex, Claude Code, and other MCP-client users configuring the repository.
- Contributors who need to understand where the skill, MCP adapter, CST execution layer, harness, references, and runtime records belong.

## Information hierarchy

The Chinese and English sections use the same order:

1. Repository identity and practical capabilities.
2. Relationship between Skill, MCP, CST execution, Harness, and references.
3. Directory structure and responsibility of each major folder.
4. Requirements, installation, and client configuration.
5. Typical end-to-end CST workflow.
6. Tool groups and optional profiles.
7. Runtime records, API extension, and vector discovery as optional advanced facilities.
8. Safety, portability, current limitations, and links to detailed documentation.

## Content boundaries

- The title is `CST 2026 Skill + MCP`.
- Direct CST operation is the primary product story.
- The API library and Harness receive one concise advanced-capabilities section.
- Detailed candidate schemas, trial payloads, promotion rules, and vector setup remain in `docs/api-development.md`.
- All examples use repository-relative paths and returned runtime identifiers.
- The README does not claim that the restructure or live CST integration has been tested when it has not.
- Existing bilingual documentation is preserved, with Chinese first and English second.

## Acceptance criteria

- A new reader can identify what the repository does before encountering API extension details.
- The repository structure table covers all major maintained directories.
- Codex and Claude users can find configuration entry points and startup commands.
- The normal connect, bind, inspect, modify, solve, read, save, and disconnect flow is explained.
- Safety gates and current implementation limits remain visible.
- API creation is clearly optional and linked to the dedicated development guide.
