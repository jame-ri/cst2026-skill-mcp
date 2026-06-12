# CST2026 MCP

`cst2026-mcp` is the standardized tool layer for this repository.

The skill stays responsible for model behavior: how to reason, when to be safe,
how to report assumptions, and how to manage CST design evolution.

The MCP server is responsible for repeatable tool calls: searching CST official
references, reading installed macro examples, extracting History/VBA patterns,
creating design records, and invoking conservative CST Python helpers.

## Run

```powershell
D:\cst2026-mcp\run-cst2026-mcp.cmd
```

The server has no npm dependencies. It speaks JSON-RPC over stdio and supports
the MCP `initialize`, `tools/list`, and `tools/call` methods.

## Suggested Codex MCP Entry

Use this command when adding the server to a Codex MCP config:

```powershell
D:\cst2026-mcp\run-cst2026-mcp.cmd
```

An example TOML snippet is available at:

```text
D:\CSTapi\mcp\codex-config.example.toml
```

After adding the MCP server to the app config, restart the Codex session. If the
tools still do not appear, verify that `run-cst2026-mcp.cmd` can be launched and
that the configured command path is absolute.

## Tool Groups

- `docs.*`: search and read CST installed macro references and copied official docs.
- `history.*`: extract compact VBA/History blocks from macros for `add_to_history()`.
- `records.*`: create and append design manifests for structure evolution, optimization, and ML data.
- `cst.*`: run standardized CST Python helper commands when `execute=true`.

## Safety Defaults

- CST project mutation tools default to `execute=false`.
- The CST helper does not call `save()` or `Save()`.
- `records.*` only writes inside this repository.
- Macro reads are limited to indexed `D:\CST\Library\Macros` files.

## Example Tool Calls

Search macros:

```json
{
  "name": "docs.search_macros",
  "arguments": {
    "query": "DiscretePort Farfield Monitor",
    "category": "Solver",
    "application": "MWS",
    "limit": 10
  }
}
```

Extract a reusable History block:

```json
{
  "name": "history.extract_pattern",
  "arguments": {
    "query": "DiscretePort",
    "max_blocks": 3
  }
}
```

Create a design manifest:

```json
{
  "name": "records.create_variant",
  "arguments": {
    "project_path": "D:\\CSTapi\\tmp_case3.cst",
    "objective": "Narrow antenna slot and compare S11 and gain",
    "save_policy": "save_copy"
  }
}
```

Plan a live parameter edit without executing:

```json
{
  "name": "cst.live_modify_parameter",
  "arguments": {
    "project_path": "D:\\CSTapi\\tmp_case3.cst",
    "parameter": "fmon",
    "test_value": 1.51,
    "pause_after_set": 5,
    "restore": true,
    "require_open": true
  }
}
```

## CST Python Helper

When `execute=true`, the MCP server calls:

```powershell
D:\CST\AMD64\python.exe D:\CSTapi\mcp\python\cst_ops.py ...
```

Override the Python path with `python_executable` or the `CST_PYTHON_EXE`
environment variable.
