# CST API + MCP Harness

[中文](#中文) | [English](#english)

## 中文

这是一个以**直接连接和操作 CST** 为核心的本地工具仓库，不是“每次先查知识库，再临时拼脚本”的系统。

```text
已知 API -> 直接调用 -> CST -> 返回真实执行结果
缺少 API -> 查官方资料 -> 编写候选 -> 授权试调用 + 后置条件检查
         -> 保存执行凭据 -> 自动注册为本地验证通过的 API -> 下次直接调用
```

向量检索只辅助发现 API。源码单独保存，已知 API 的调用不依赖向量模型、文档检索或文本记忆。

### 目录职责

| 目录 | 职责 |
| --- | --- |
| `cst_api/` | CST 会话、参数、求解器、结果读取和扩展代码执行 |
| `api_library/` | API 目录、候选快照、版本注册、检索和停用 |
| `harness/` | 执行意图、结果凭据、重复操作保护及辅助记忆 |
| `mcp/` | MCP 协议、工具适配和旧入口兼容 |
| `shared/` | 相对路径约束、输入校验、原子写入和子进程支持 |
| `skills/` | agent 的工作规则，不承载另一套 CST 实现 |
| `config/` | 通用 MCP、Codex 和环境配置示例 |
| `docs/` | 架构与扩展开发说明；旧草稿在 `docs/archive/` |
| `official-docs/`, `macro-library/`, `domain-guides/` | 原有参考资料，只有缺少能力时才查 |
| `design-records/` | 本地执行记录与学到的 API，默认不纳入 Git |

用户工程、探测数据和原有临时脚本保持原位置，没有作为框架代码迁移。

### 安装与连接

1. 准备 Node.js 18+。MCP 核心只使用 Node 内置模块，不需要安装 npm 依赖。
2. 实际操作 CST 时，需要有许可的本地 CST 和与其 Python 绑定兼容的解释器。通过 `CST_PYTHON_EXE`、`CST_INSTALL_DIR` 或 `CST_PYTHON_LIB_DIR` 配置机器环境。
3. 从仓库根目录启动 agent，并使用 [通用 MCP 配置](config/mcp-client.example.json) 或 [Codex 配置](config/codex.example.toml)。Claude Code 等支持 MCP 的 agent 可使用同一个服务，只需按客户端格式配置。
4. 按 agent 自身的 skill 机制载入 [SKILL.md](skills/cst-python-automation/SKILL.md)。不支持 skill 的客户端可将其作为项目规则；MCP 本身不依赖特定 agent。
5. 重启 MCP 连接以加载新的工具列表。修改仓库不会自动更新你以前安装在其他目录的 skill 副本。

手动启动服务：

```sh
node mcp/src/server.js
```

也可使用根目录的 `run-cst2026-mcp.cmd` 或 `run-cst2026-mcp.sh`，启动脚本会以自身位置确定仓库目录。服务使用 stdio，由 MCP 客户端负责连接，不是 HTTP 服务。

**工作目录很重要：** 配置中的脚本路径相对服务启动目录。桌面客户端不一定从仓库启动，需要设置服务工作目录，或使用已放入 PATH 的启动器。配置格式和工作目录行为由具体客户端决定；不要直接照搬不受支持的 `cwd` 字段。

### 默认工具

默认 `CST_MCP_PROFILE=control`，提供以下 19 个工具：

| 用途 | 工具 |
| --- | --- |
| 连接与状态 | `cst.connect`, `cst.disconnect`, `cst.session_status` |
| 工程 | `cst.open_project`, `cst.save_project` |
| 参数 | `cst.get_parameters`, `cst.set_parameters` |
| 求解 | `cst.run_solver`, `cst.solver_status`, `cst.stop_solver` |
| 结果 | `cst.list_results`, `cst.read_result` |
| API 发现与调用 | `api.search`, `api.describe`, `api.call` |
| 扩展闭环 | `api.stage`, `api.trial`, `api.retire`, `api.reindex` |

设置 `CST_MCP_PROFILE=full` 可额外使用原有资料检索、文本记忆、记录和恢复工具。它们不是常规调用的前置步骤。直接会话存续期间，服务阻止混用大部分旧 CST 控制工具。

### 如何使用

这些是 MCP 工具参数，不是 shell 命令。所有 CST 工具默认 `execute=false`，包括实时读取；实际读取也需要明确执行。

先连接已存在的 CST：

```json
{"name":"cst.connect","arguments":{"mode":"existing","execute":true}}
```

存在多个实例时指定 `pid`。没有实例不会偷偷新建，只有明确使用 `mode="new"` 才会创建。

之后按以下顺序调用，使用工具实际返回的 `session_id`、`project_id` 和 `job_id`：

1. `cst.open_project`：选择仓库内已有的相对路径 `.cst` 文件。
2. `cst.get_parameters`：读取真实参数名、表达式和可用数值。
3. 如需保护原工程，先 `cst.save_project`，选择 `save_copy` 和不同的 `save_copy_path`。
4. `cst.set_parameters`：修改已存在的参数，不自动保存；默认重建模型。
5. 用户授权求解后，`cst.run_solver` 使用 `execute=true` 和 `allow_solve=true`。
6. `cst.solver_status` 查询实际状态。返回“不在运行”不等于求解成功。
7. `cst.list_results` 后，用明确的 `tree_path` 和 `run_id` 调用 `cst.read_result`。
8. 需要保存时单独调用保存工具；最后 `cst.disconnect` 只释放连接，不关闭 CST、不保存、不停止求解。

已知 API 也可统一通过 `api.call` 调用，不需要先搜索：

```json
{
  "name": "api.call",
  "arguments": {
    "api_id": "cst.get_parameters",
    "arguments": {
      "session_id": "<实际返回的 session_id>",
      "project_id": "<实际返回的 project_id>",
      "execute": true
    }
  }
}
```

### 自动入库

[API 开发说明](docs/api-development.md) 给出完整格式和示例。

1. 确认现有 API 没有覆盖，再查官方资料。
2. 编写参数化 Python 实现、独立的 `verify` 函数和候选 JSON。
3. `api.stage` 加 `execute=true` 保存不可变快照，不运行源码。
4. 审阅代码，并在 MCP 服务环境启用 `CST_ENABLE_API_EXTENSIONS=1`。
5. `api.trial` 的 `arguments` 中显式设置 `execute=true`、`allow_extension_execution=true`；求解类还需要 `allow_solve=true`。
6. 只有实际调用通过检查且执行凭据保存成功，才默认自动注册为 `locally_verified`。以后用带版本的精确 ID，例如 `user.parameter_report@1.0.0`。
7. 已注册接口后续验证失败会标记为 `disputed`，不再作为正常可调用接口；修复应使用新版本，或通过 `api.retire` 停用。

**扩展 Python 不是沙箱。** 它拥有服务进程的权限；“只读”声明不是权限隔离。只对已审阅、已授权的源码启用执行。示例接口尚未经过真实 CST 验证，不会预先注册。

### 可选向量检索

默认不安装模型、不下载模型，也不依赖向量库才能操作 CST。

需要时，单独为检索 Python 环境安装 `harness/requirements-vector.txt` 中的可选依赖，准备完整的本地模型目录，并设置：

```text
CST_EMBEDDING_MODEL=models/your-local-model
CST_EMBEDDING_MODEL_ID=your-model-revision
CST_EMBEDDING_PYTHON=python
```

然后显式调用 `api.reindex`，设置 `execute=true`。`api.search` 的 `mode="vector"` 使用本地语义检索；`auto` 不可用时明确返回关键词降级说明。模型权重改变后必须更新 revision 并重建索引。

### 边界与安全

- 仓库配置、工具工程路径、候选文件和模型目录使用相对路径，拒绝越界和路径链接。安装位置由环境或系统发现，供运行时解析，不硬编码到示例或 API 定义。
- 默认针对已有工程；新建工程、完整几何/端口/边界配置及所有结果类型并未全部内置。当前直接结果读取覆盖 0D/1D，不应冒充完整 CST SDK。
- 求解提交、求解结束、结果新鲜度和电磁有效性是不同状态；结果不会默认认定属于刚才的求解。
- 修改可能部分生效。超时或丢失连接后的未知结果不能自动重放。
- 相同 `operation_id` 只返回既有凭据，不再次执行；旧会话 ID 在 worker 丢失后无效。
- 正常退出尽量释放协作租约；强制超时可能留下租约，须核实进程归属后人工处理。不要同时用 GUI 或其他控制器修改同一工程。
- 本次架构重整未运行新代码的测试、实际 CST 调用或模型安装，不能据此声称已通过运行验证。

更多内容：[架构](docs/architecture.md) · [MCP 说明](mcp/README.md) · [环境变量](config/environment.example)

## English

This repository is a **direct CST API layer exposed through MCP**, with a harness for evidence-backed local API reuse. It is not a mandatory document-search pipeline.

```text
Known API -> direct invocation -> CST -> actual outcome
Missing API -> official references -> candidate implementation -> authorized trial + verifier
            -> durable execution receipt -> local registration -> direct reuse
```

### Setup

1. Install Node.js 18+. The MCP core uses built-in Node modules and has no npm dependencies.
2. Actual CST execution requires a licensed local installation and a compatible vendor Python environment. Configure `CST_PYTHON_EXE`, `CST_INSTALL_DIR` or `CST_PYTHON_LIB_DIR` as needed.
3. Start your agent from the repository root and adapt the [generic MCP configuration](config/mcp-client.example.json) or [Codex configuration](config/codex.example.toml) to your client.
4. Load the repository [skill](skills/cst-python-automation/SKILL.md) using the agent's own skill mechanism, or use it as project instructions. Codex, Claude Code and other MCP clients share the same server.
5. Restart the MCP connection after configuration changes. Previously installed skill copies are not updated automatically.

Start the stdio service with `node mcp/src/server.js`, or the platform launcher in the repository root. This is not an HTTP service.

Relative script arguments require the server's working directory to be the repository root. Desktop clients may need an explicitly configured working directory or a launcher on PATH. Do not assume every client accepts a `cwd` configuration field.

### Architecture and tools

`cst_api/` executes CST operations; `api_library/` manages reusable APIs; `harness/` stores execution evidence; `mcp/` exposes tools. `skills/` contains agent instructions, `config/` contains examples, and local generated data stays under ignored `design-records/`. Existing engineering projects and reference collections are preserved.

The default `control` profile exposes 12 direct CST tools and 7 API-library tools listed above. Set `CST_MCP_PROFILE=full` to additionally expose legacy retrieval, memory and recovery tools. Retrieval is never a prerequisite for known APIs.

### Typical workflow

1. Call `cst.connect` with `mode="existing"` and `execute=true`. Specify a PID when multiple instances exist; creation requires explicit `mode="new"`.
2. Bind an existing repository-relative project with `cst.open_project`.
3. Read parameters, save a copy if needed, and modify named parameters.
4. With user authorization, call `cst.run_solver` with `execute=true` and `allow_solve=true`; poll `cst.solver_status` using the returned job ID.
5. List results, then read an explicit tree path and run ID. Check provenance and freshness before interpreting the data.
6. Save explicitly. Disconnecting does not save, close CST or stop a solver.

Use the actual returned session/project/job IDs. All direct tools, including live reads, default to plan-only. A known tool may also be invoked through `api.call` using its exact `api_id` and nested `arguments`, without any search.

### Extending and learning

Define a versioned candidate JSON, parameterized Python implementation and separate postcondition verifier. Stage it with `api.stage`; staging only snapshots source and reference hashes.

After reviewing the source, explicitly enable `CST_ENABLE_API_EXTENSIONS=1` and authorize `api.trial` with nested `execute=true` and `allow_extension_execution=true`. Solver extensions additionally require `allow_solve=true`.

A passing trial with a durable execution receipt registers that exact version as `locally_verified` by default. Invoke it later by an exact ID such as `user.parameter_report@1.0.0`. A subsequent verification failure disputes the API; repairs require a new version. `api.retire` disables reuse without deleting evidence.

**Python extensions are not sandboxed.** They run with the server's privileges. A passing author-supplied verifier proves only its local postconditions, not universal correctness or electromagnetic validity. The bundled example is unverified and not pre-registered. See [API development](docs/api-development.md).

### Optional semantic discovery

Install the optional Python dependency explicitly, provision a trusted complete local model, configure `CST_EMBEDDING_MODEL`, `CST_EMBEDDING_MODEL_ID` and optionally `CST_EMBEDDING_PYTHON`, then call `api.reindex` with `execute=true`.

Only API descriptions and schemas are embedded. Code remains a separate immutable artifact. No dependency installation or model download happens automatically. Exact-ID calls bypass vectors; automatic fallback identifies keyword search honestly. Change the revision and rebuild after changing model weights.

### Limits and execution status

Project/artifact inputs are repository-relative; machine bindings are resolved from the environment rather than hardcoded. CST may require resolved absolute paths internally, but those are not portable API definitions.

This is not a complete vendor SDK wrapper: the bundled operations focus on existing projects, parameters, tracked solver jobs and 0D/1D results. Solver submission or a non-running state does not prove success. Result freshness and physical validity require separate evidence.

Mutations may partially succeed. Never automatically replay an uncertain operation. Reusing an operation ID returns its receipt instead of rerunning it. Worker loss invalidates live IDs; forced termination may leave a lease requiring owner-aware manual recovery.

**The restructuring has not been tested against a running CST installation, and no new tests, model installations or indexing runs were performed as part of it.**
