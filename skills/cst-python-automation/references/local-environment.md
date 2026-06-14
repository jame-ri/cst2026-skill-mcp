# Local CST Environment Cache

Use these paths before rediscovering the CST installation on this machine.

## Environment Variables

| Name | Value |
| --- | --- |
| `CST_PYTHON_EXE` | `D:\CST\Python\python.exe` |
| `CST_STUDIO_EXE` | `D:\CST\AMD64\CST DESIGN ENVIRONMENT_AMD64.exe` |
| `CST_API_ROOT` | `D:\CSTapi` |
| `CST_MCP_ROOT` | `D:\CSTapi\mcp` |
| `CST_OFFICIAL_DOCS` | `D:\CSTapi\official-docs` |
| `CST_MACRO_LIBRARY` | `D:\CSTapi\macro-library` |

## Usage

- Run CST automation scripts with `%CST_PYTHON_EXE%` / `$env:CST_PYTHON_EXE` unless the user explicitly provides another CST Python executable.
- Use `%CST_API_ROOT%` for local CST MCP helper scripts, copied official docs, macro inventory, and domain guides.
- If one of these paths fails, verify the path once, update both the Windows user environment variable and this cache file, then continue.
