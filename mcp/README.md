# CST2026 MCP

`cst2026-mcp` is the standardized tool layer for this repository.

The skill stays responsible for model behavior: how to reason, when to be safe,
how to report assumptions, and how to manage CST design evolution.

The MCP server is responsible for repeatable tool calls: searching CST official
references, reading installed macro examples, extracting History/VBA patterns,
creating design records, and invoking conservative CST Python helpers.

## Run

```powershell
D:\CSTapi\run-cst2026-mcp.cmd
```

The server has no npm dependencies. It speaks JSON-RPC over stdio and supports
the MCP `initialize`, `tools/list`, and `tools/call` methods.

## Local CST Path Configuration

CST installation paths vary by machine. The launch script and MCP server use
this order:

1. Explicit environment variables from the Codex MCP config or shell.
2. Auto-detection of common CST 2026 install paths.
3. Tool-call override fields such as `python_executable`.

Supported environment variables:

| Variable | Purpose | Example on this machine |
| --- | --- | --- |
| `CST_INSTALL_DIR` | CST installation root | `D:\CST` |
| `CST_PYTHON_EXE` | CST bundled Python used for `cst.interface` / `cst.results` | `D:\CST\Python\python.exe` |
| `CST_MACRO_ROOT` | Installed CST macro library root | `D:\CST\Library\Macros` |
| `CST_DESIGN_ENV_EXE` | CST Design Environment executable, for diagnostics/documentation | `D:\CST\CST DESIGN ENVIRONMENT.exe` |

The current machine was verified with:

```text
CST_INSTALL_DIR=D:\CST
CST_PYTHON_EXE=D:\CST\Python\python.exe
CST_MACRO_ROOT=D:\CST\Library\Macros
CST_DESIGN_ENV_EXE=D:\CST\CST DESIGN ENVIRONMENT.exe
```

If CST is installed somewhere else, set the environment variables in the MCP
configuration instead of editing source code.

## Suggested Codex MCP Entry

Use this command when adding the server to a Codex MCP config:

```powershell
D:\CSTapi\run-cst2026-mcp.cmd
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
- `cst.inspect_project`: read-only project state, open projects, messages, model tree, and result-tree discovery.
- `cst.inspect_geometry`: read-only, tree-derived geometry inventory for the Physical Structure Gate.
- `cst.inspect_physics_setup`: read-only checklist for materials, ports, boundaries, mesh, monitors, solver/result evidence, and CST messages.
- `cst.result_sanity`: read saved CST result trees and run compact checks such as passive S-parameter `|S| <= 1`.
- `cst.process_status`: inspect CST-related process, memory, and disk state.
- `cst.preflight_resources`: block long jobs when process count, memory, or disk thresholds are unsafe.
- `cst.job_checkpoint` / `cst.recover_job`: record and resume multi-stage CST jobs.
- `cst.cleanup_stale_processes`: plan or explicitly terminate selected stale PIDs; it never kills by name.
- `cst.closed_start` / `cst.live_modify_parameter`: controlled CST helper commands when `execute=true`.
- `cst.close_project`: close a specified CST project with explicit `no_save`, `save_copy`, or `save_original` policy.

## Safety Defaults

- CST project mutation tools default to `execute=false`.
- CST inspect/result sanity tools also default to `execute=false`; they return the planned CST Python command until explicitly executed.
- Resource/process inspection tools default to `execute=false`; run them with `execute=true` before long jobs.
- Process cleanup requires explicit `pids`, `execute=true`, and `allow_terminate=true`.
- CST helpers do not save by default. `cst.close_project` calls `Project.close()` for `no_save`; it calls `Project.save(...)` only when `save_policy` is explicitly `save_copy` or `save_original`.
- `records.*` only writes inside this repository.
- Macro reads are limited to the detected CST macro root, normally
  `%CST_MACRO_ROOT%` or `<CST_INSTALL_DIR>\Library\Macros`.

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

Plan a read-only project inspection:

```json
{
  "name": "cst.inspect_project",
  "arguments": {
    "project_path": "D:\\CSTapi\\tmp_case3.cst",
    "include_results": true,
    "max_tree_items": 300
  }
}
```

Close a project without triggering a GUI save prompt:

```json
{
  "name": "cst.close_project",
  "arguments": {
    "project_path": "D:\\CSTapi\\tmp_case3.cst",
    "save_policy": "no_save",
    "require_open": true
  }
}
```

Save a job copy and then close it:

```json
{
  "name": "cst.close_project",
  "arguments": {
    "project_path": "D:\\CSTapi\\tmp_case3.cst",
    "save_policy": "save_copy",
    "save_copy_path": "D:\\CSTapi\\runs\\tmp_case3_reviewed.cst",
    "allow_overwrite": false,
    "require_open": true
  }
}
```

Inspect existing geometry evidence before a model edit:

```json
{
  "name": "cst.inspect_geometry",
  "arguments": {
    "project_path": "D:\\CSTapi\\tmp_case3.cst",
    "require_open": true,
    "max_tree_items": 500
  }
}
```

Check physics setup before solving:

```json
{
  "name": "cst.inspect_physics_setup",
  "arguments": {
    "project_path": "D:\\CSTapi\\tmp_case3.cst",
    "max_tree_items": 500
  }
}
```

Plan result sanity checks:

```json
{
  "name": "cst.result_sanity",
  "arguments": {
    "project_path": "D:\\CSTapi\\tmp_case3.cst",
    "passive": true
  }
}
```

Run a long-job resource preflight:

```json
{
  "name": "cst.preflight_resources",
  "arguments": {
    "project_path": "D:\\CSTapi\\tmp_case3.cst",
    "min_free_memory_gb": 12,
    "min_free_disk_gb": 20,
    "max_cst_processes": 1,
    "execute": true
  }
}
```

Record a checkpoint:

```json
{
  "name": "cst.job_checkpoint",
  "arguments": {
    "job_id": "tmp-case3-sweep",
    "project_path": "D:\\CSTapi\\tmp_case3.cst",
    "stage": "preflight",
    "status": "done",
    "detail": "Resource gate passed before geometry mutation."
  }
}
```

Recover a job after interruption:

```json
{
  "name": "cst.recover_job",
  "arguments": {
    "job_id": "tmp-case3-sweep"
  }
}
```

Plan selected PID cleanup:

```json
{
  "name": "cst.cleanup_stale_processes",
  "arguments": {
    "pids": [12345],
    "force": false
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
%CST_PYTHON_EXE% D:\CSTapi\mcp\python\cst_ops.py ...
```

Override the Python path with the tool argument `python_executable` or the
`CST_PYTHON_EXE` environment variable. On this machine the working CST Python is
`D:\CST\Python\python.exe`.
