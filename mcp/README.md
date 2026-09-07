# MCP adapter / MCP 接入层

MCP 的职责是把 CST API 暴露给 agent，不承担另一套 CST 实现，也不强制先检索资料。

The stdio MCP adapter exposes the same CST controller and versioned API library to different agents.

## 启动 / Start

From the repository root:

```sh
node mcp/src/server.js
```

Requirements: Node.js 18+; no npm dependencies for the server core. Live CST calls additionally require the installed CST vendor bindings and a compatible Python interpreter.

Configuration examples: [generic MCP](../config/mcp-client.example.json), [Codex](../config/codex.example.toml), [environment variables](../config/environment.example). Relative script arguments require a known working directory. Desktop clients may need a launcher rather than the same configuration syntax as a CLI agent.

## 工具配置 / Profiles

- `CST_MCP_PROFILE=control` is the default: 12 direct CST tools plus 7 API-library tools.
- `CST_MCP_PROFILE=full` additionally exposes the original document/macro lookup, textual workflow memory, records and legacy CST helpers.
- A known API never requires a search call. Use `cst.*` directly, or `api.call`.
- Do not mix legacy CST mutation helpers with an active direct session. Most legacy CST tools are blocked while a direct controller is active.

See the [root README](../README.md) for the complete default tool list and bilingual usage steps.

## 输入与结果 / Contracts

- All tools publish object input schemas. Unknown top-level arguments are rejected.
- Missing JSON-RPC `params` may be normalized to an empty object; explicit `params:null`, arrays and other invalid types are rejected rather than treated as an absent parameter.
- Direct CST tools default to `execute=false`, including live reads. A plan does not connect or create a CST instance.
- `api.call` and `api.trial` put execution controls inside their nested `arguments` object.
- CST solve/stop and arbitrary local extension execution require their own explicit authorization gates.
- Tool project/artifact paths are repository-relative. Paths cannot escape through dot segments, symlinks or junctions.
- Execution errors are returned as tool results, separately from protocol/argument errors.
- Solver submission is asynchronous. Not running does not prove successful simulation.
- An identical `operation_id` returns its prior receipt; it does not execute again. Incomplete receipts block automatic replay.
- `api.trial` returns both the execution outcome and a separate `registration` outcome.
- Extensions run with the server's permissions, not in a sandbox. Default extension execution is disabled.

## 实现位置 / Source ownership

- `src/mcp-protocol.js`: framing, JSON-RPC and MCP response formatting.
- `src/server.js`: service entry, profile selection, dispatch and retained legacy adapters.
- `src/api-tools.js`: API-library tool schemas and routing.
- `../cst_api/`: actual CST execution.
- `../api_library/`: candidate storage, discovery, registration and versioned calls.
- `../harness/`: execution receipts and auxiliary workflow memory.
- Old Python and JavaScript entry filenames remain compatibility shims.

No live CST run or new test execution was performed during this restructuring.
