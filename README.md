# CSTapi

This repository is a CST Studio Suite automation knowledge base for AI agents.

It contains:

- Bilingual CST automation skill guides in `skills/`
- A no-dependency MCP server for standardized CST reference and helper tools in `mcp/`
- Bilingual domain guides for complex antenna design evolution in `domain-guides/`
- A searchable CST installed macro index and usage guide in `macro-library/`
- Local copies of CST official automation-related documentation in `official-docs/`
- A source index for additional CST documentation installed under `D:\CST`

The intended split is:

- Skill files define model behavior, safety rules, and CST workflow strategy.
- MCP tools provide standardized calls for macro search, official-doc reads, History/VBA extraction, design records, and conservative CST Python helpers.

Start here:

- Chinese guide: `skills/cst-python-automation.zh-CN.md`
- English guide: `skills/cst-python-automation.en.md`
- MCP server: `mcp/README.md`
- MCP launch command: `run-cst2026-mcp.cmd`
- Antenna design evolution: `domain-guides/design-evolution.zh-CN.md`
- Geometry mutation guide: `domain-guides/geometry-mutation.zh-CN.md`
- Result diagnosis guide: `domain-guides/result-diagnosis.zh-CN.md`
- Optimization, data, and model versioning: `domain-guides/optimization-ml-data.zh-CN.md`
- CST macro usage guide: `macro-library/cst-macro-usage.zh-CN.md`
- CST macro searchable inventory: `macro-library/macro-inventory.csv`
- Official source index: `official-docs/source-index.md`
