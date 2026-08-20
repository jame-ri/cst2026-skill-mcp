# Local CST Environment

CST installation paths are machine-specific. Configure them via environment
variables rather than hardcoding absolute paths.

## Environment Variables

| Name | Purpose |
| --- | --- |
| `CST_INSTALL_DIR` | CST installation root |
| `CST_PYTHON_EXE` | CST bundled Python executable (for `cst.interface` / `cst.results`) |
| `CST_MACRO_ROOT` | Installed CST macro library root |
| `CST_DESIGN_ENV_EXE` | CST Design Environment executable |
| `CST_API_ROOT` | Repository root (auto-detected from script location if unset) |

## Usage

- Set these in your shell profile, agent MCP config, or the launch script.
- The MCP server auto-detects common CST 2026 install paths (under
  `C:\Program Files\...` on Windows) when environment variables are unset.
- See `mcp/config/` for agent-specific configuration examples.
- If a path fails, verify it once and update the environment variable;
  do not edit source code.
