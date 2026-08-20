# Agent Configuration

cst2026-mcp is agent-agnostic. Any MCP-compatible client can connect to it.
This directory provides configuration examples for common agents.

## Supported Agents

| Agent | Config format | Example file |
| --- | --- | --- |
| Codex | TOML | `codex.example.toml` |
| Claude Desktop / Claude Code | JSON | `claude.example.json` |
| Cursor | JSON | `cursor.example.json` |

The agent registry is defined in `agents.json`.

## Quick Start

1. Copy the example config for your agent.
2. Fill in the `CST_*` environment variables to match your local CST installation
   (or leave them empty to use auto-detection of common install paths).
3. Add the config to your agent's MCP settings.
4. Restart the agent session.

## Environment Variables

All agents share the same CST environment variables:

| Variable | Purpose |
| --- | --- |
| `CST_INSTALL_DIR` | CST installation root |
| `CST_PYTHON_EXE` | CST bundled Python executable |
| `CST_MACRO_ROOT` | Installed CST macro library root |
| `CST_DESIGN_ENV_EXE` | CST Design Environment executable |

When unset, the MCP server auto-detects common CST 2026 install paths under
`C:\Program Files\...` on Windows.

## Adding a New Agent

1. Create a config example file in this directory (e.g., `myagent.example.json`).
2. Add an entry to `agents.json`:

```json
"myagent": {
  "name": "My Agent",
  "config_format": "json",
  "config_example": "myagent.example.json",
  "launch_command": "node mcp/src/server.js",
  "description": "My custom agent"
}
```

3. Set the `CST_*` environment variables in the agent's MCP config.
4. Run `npm test` from the `mcp/` directory to validate the new config.
