# CST agent

This repository is a CST Studio Suite automation knowledge base for AI agents.

It contains:

- Bilingual CST automation skill guides in `skills/`
- An installable CST automation skill in `skills/cst-python-automation/SKILL.md`
- A no-dependency MCP server for standardized CST reference and helper tools in `mcp/`
- Agent configuration examples for Codex, Claude, and Cursor in `mcp/config/`
- Bilingual domain guides for complex antenna design evolution in `domain-guides/`
- A searchable CST installed macro index and usage guide in `macro-library/`
- Local copies of CST official automation-related documentation in `official-docs/`
- A source index for additional CST documentation installed with the local CST copy

The intended split is:

- Skill files define model behavior, safety rules, and CST workflow strategy.
- MCP tools provide standardized calls for macro search, official-doc reads, History/VBA extraction, design records, and conservative CST Python helpers.

Start here:

- Installable skill: `skills/cst-python-automation/SKILL.md`
- Chinese guide: `skills/cst-python-automation.zh-CN.md`
- MCP server: `mcp/README.md`
- Agent configs: `mcp/config/README.md`
- MCP launch (Windows): `run-cst2026-mcp.cmd`
- MCP launch (macOS/Linux): `run-cst2026-mcp.sh`
- Antenna design evolution: `domain-guides/design-evolution.zh-CN.md`
- Geometry mutation guide: `domain-guides/geometry-mutation.zh-CN.md`
- Result diagnosis guide: `domain-guides/result-diagnosis.zh-CN.md`
- Optimization, data, and model versioning: `domain-guides/optimization-ml-data.zh-CN.md`
- CST macro usage guide: `macro-library/cst-macro-usage.zh-CN.md`
- CST macro searchable inventory: `macro-library/macro-inventory.csv`
- Official source index: `official-docs/source-index.md`

## Local CST Path Configuration

CST installation paths are machine-specific. Configure them via environment
variables — do not hardcode absolute paths in source or config.

| Variable | Purpose |
| --- | --- |
| `CST_INSTALL_DIR` | CST installation root |
| `CST_PYTHON_EXE` | CST bundled Python executable |
| `CST_MACRO_ROOT` | Installed CST macro library root |
| `CST_DESIGN_ENV_EXE` | CST Design Environment executable |

The launch script (`run-cst2026-mcp.cmd` / `run-cst2026-mcp.sh`) auto-detects
common CST 2026 install paths when environment variables are unset. See
`mcp/config/` for agent-specific configuration examples.
