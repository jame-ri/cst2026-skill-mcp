# CST2026 MCP

A small dependency-free Model Context Protocol server for CST2026.

## Run

```powershell
node .\src\server.js
```

The server speaks MCP over stdio, so it is meant to be launched by an MCP client rather than used directly in a terminal.

## Tools

- `cst2026_ping`: returns a simple health response.
- `cst2026_project_info`: returns the server name, version, and workspace path.
- `cst2026_cst_info`: inspects the local CST installation, defaulting to `D:\CST`.
- `cst2026_echo`: echoes a message; useful for client wiring tests.

## Example Client Config

Use the absolute path for this repository on your machine:

```json
{
  "mcpServers": {
    "cst2026": {
      "command": "node",
      "args": [
        "D:\\Backup\\Documents\\New project\\src\\server.js"
      ]
    }
  }
}
```

## Notes

This server intentionally avoids external packages so it can run in the current environment where `node` is available but `npm` is not on PATH. If package management is added later, it can be migrated to `@modelcontextprotocol/sdk` without changing the tool names.
