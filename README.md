# CST 2026 Skill + MCP

[中文](#中文) | [English](#english)

面向 Codex、Claude Code 等 agent 的 CST Studio Suite 2026 自动化 Skill 与 MCP 服务。

Agent instructions and an MCP server for operating CST Studio Suite 2026 from Codex, Claude Code, and other MCP-compatible clients.

## 中文

### 项目简介

本仓库将 CST 自动化所需的几部分组织在同一个可移植项目中：

- **Skill** 告诉 agent 如何选择工具、控制风险、验证结果和处理异常。
- **MCP 服务**向不同 agent 提供统一的 CST 工具接口。
- **CST 执行层**负责连接 CST、操作工程、读取参数、调用求解器和读取结果。
- **Harness** 记录操作意图和执行结果，避免不确定的修改被自动重复执行。
- **参考资料**在现有工具无法满足任务时，帮助排查问题和扩充能力。

日常主线是“agent 调用 MCP 工具直接操作 CST”。API 扩展、知识记录和向量检索属于可选高级功能，不是每次操作的前置步骤。

### 主要能力

| 类别 | 当前能力 |
| --- | --- |
| CST 连接 | 连接指定的现有 CST 实例，或在明确要求时创建新实例；查询状态并安全释放连接 |
| 工程管理 | 打开或绑定仓库内已有的 `.cst` 工程；保存副本或在明确授权后保存原工程 |
| 参数操作 | 枚举参数，读取表达式和数值，批量修改参数并重建 History |
| 求解器 | 启动当前工程配置的求解器，查询状态，停止由当前会话提交的任务 |
| 结果读取 | 浏览 CST 0D/1D 结果树，按 `run_id` 分页读取标量、曲线和复数数据 |
| 执行保护 | 默认只生成计划；修改前记录意图；相同操作 ID 不重复执行；未知结果要求人工检查 |
| 兼容与恢复 | 完整配置下保留文档、宏、记录、资源检查、恢复和文本知识工具 |
| 能力扩展 | 缺少工具时，可将经过审阅和真实试调用验证的实现注册为本地版本化能力 |

当前实现重点服务于已有 CST 工程，不是 CST 官方 SDK 的完整替代品。完整新建模型、所有几何/材料/端口/边界操作以及全部结果类型仍需要继续扩充。

### 工作方式

```text
用户任务
   |
   v
Codex / Claude / 其他 agent
   |  读取 Skill，选择和组合工具
   v
MCP 服务
   |  参数校验、授权检查、结果封装
   v
CST 执行层 ---- Harness 执行记录
   |
   v
CST Studio Suite
```

Skill 与 MCP 相互配合，但不绑定同一种 agent。支持 MCP 的客户端可以使用同一个服务；不支持 Skill 目录约定的客户端，也可以将 [Skill 规则](skills/cst-python-automation/SKILL.md)作为项目说明。

### 仓库结构

| 路径 | 作用 |
| --- | --- |
| `skills/cst-python-automation/` | CST 自动化 Skill、工作流程、安全规则和领域参考 |
| `mcp/` | MCP stdio 服务入口、协议处理、工具适配、兼容入口和测试 |
| `cst_api/` | CST 会话、工程、参数、求解器、结果读取和扩展执行实现 |
| `harness/` | 操作日志、重复执行保护、辅助知识记录和可选嵌入适配器 |
| `api_library/` | 内置/扩展能力目录、候选快照、版本注册与可选检索 |
| `shared/` | 相对路径检查、输入校验、原子写入和子进程工具 |
| `config/` | 通用 MCP、Codex 和环境变量配置示例 |
| `docs/` | 架构、扩展开发和归档设计说明 |
| `official-docs/` | 随仓库保存的 CST 官方 API 参考资料 |
| `macro-library/` | CST 宏与脚本清单 |
| `domain-guides/` | CST/RF 领域工作说明 |
| `design-records/` | 本地执行记录、检查点和已验证扩展；默认不提交 Git |
| `scripts/` | 原有或临时的本地脚本，不作为 MCP 主入口 |

工程文件和实验数据可以放在仓库内单独目录中。框架使用仓库相对路径引用它们，不在 Skill、配置和可复用能力中固化某台机器的绝对路径。

### 环境要求

- Node.js 18 或更高版本。MCP 核心仅使用 Node.js 内置模块，不需要安装 npm 依赖。
- 本地安装并获得许可的 CST Studio Suite 2026。
- 能够导入 CST Python 库的 Python 解释器。
- 支持 stdio MCP 的 agent 客户端，例如 Codex 或 Claude Code。

常用环境变量见 [config/environment.example](config/environment.example)：

| 变量 | 用途 |
| --- | --- |
| `CST_PYTHON_EXE` | 指定兼容 CST Python 绑定的解释器 |
| `CST_INSTALL_DIR` | 指定 CST 安装目录；未设置时尝试从系统环境发现 |
| `CST_PYTHON_LIB_DIR` | 直接指定 `python_cst_libraries` 所在目录 |
| `CST_MCP_PROFILE` | `control` 为默认直接控制工具；`full` 额外启用兼容工具 |
| `CST_ENABLE_API_EXTENSIONS` | 是否允许执行经过审阅的本地扩展 Python；默认关闭 |
| `CST_API_LIBRARY_DIR` | 本地扩展和注册记录目录，必须是仓库相对路径 |

### 快速开始

1. 克隆仓库并进入仓库根目录。
2. 根据本机 CST 安装设置必要的环境变量。
3. 在 agent 中配置 MCP 服务。
4. 将仓库 Skill 安装到 agent 的 Skill 目录，或作为项目规则引用。
5. 重启 MCP 连接，确认工具列表已经加载。

通用配置参考 [config/mcp-client.example.json](config/mcp-client.example.json)：

```json
{
  "mcpServers": {
    "cst-api": {
      "command": "node",
      "args": ["mcp/src/server.js"],
      "env": {
        "CST_MCP_PROFILE": "control",
        "CST_ENABLE_API_EXTENSIONS": "0"
      }
    }
  }
}
```

Codex 可参考 [config/codex.example.toml](config/codex.example.toml)。Claude Code 和其他客户端使用相同的 `node mcp/src/server.js` 服务命令，但配置文件位置和字段以各客户端文档为准。

相对脚本路径要求 MCP 服务从仓库根目录启动。如果客户端不能设置工作目录，可使用根目录的 `run-cst2026-mcp.cmd` 或 `run-cst2026-mcp.sh`。也可以直接运行 `node mcp/src/server.js`。该进程使用 stdio 与 MCP 客户端通信，不是 HTTP 服务。

### 典型使用流程

用户可以直接用自然语言向 agent 描述任务，例如：

> 连接当前 CST 实例，打开 `projects/filter.cst`，读取全部参数，把 `gap` 改为 `0.25`，保存到 `outputs/filter-gap-025.cst`。先不要运行求解器。

agent 应按以下顺序工作：

1. 使用 `cst.connect` 连接明确的 CST 实例。存在多个实例时选择 PID；不会自动创建新实例。
2. 使用 `cst.open_project` 打开或绑定仓库内已有工程，并保存返回的 `session_id` 和 `project_id`。
3. 读取真实参数、工程状态或结果树，不猜测参数名和结果路径。
4. 修改前根据风险保存工程副本；修改参数不会自动保存工程。
5. 只有获得用户授权后，才以 `allow_solve=true` 调用求解器。
6. 使用返回的 `job_id` 查询实际状态。求解器停止不等于仿真成功。
7. 读取结果时明确指定结果树路径和 `run_id`，并检查新鲜度、单位和工程状态。
8. 根据用户要求单独保存，最后释放连接。断开连接不会关闭 CST、保存工程或停止求解器。

所有直接 CST 工具默认 `execute=false`。此时只返回执行计划，不会连接、读取或修改 CST；真正执行时必须显式设置 `execute=true`。

### 工具与配置模式

默认 `CST_MCP_PROFILE=control` 提供 19 个工具：

| 用途 | 工具 |
| --- | --- |
| 会话 | `cst.connect`, `cst.disconnect`, `cst.session_status` |
| 工程 | `cst.open_project`, `cst.save_project` |
| 参数 | `cst.get_parameters`, `cst.set_parameters` |
| 求解器 | `cst.run_solver`, `cst.solver_status`, `cst.stop_solver` |
| 结果 | `cst.list_results`, `cst.read_result` |
| 能力目录 | `api.search`, `api.describe`, `api.call` |
| 可选扩展管理 | `api.stage`, `api.trial`, `api.retire`, `api.reindex` |

设置 `CST_MCP_PROFILE=full` 后，还会提供原仓库中的文档/宏检索、工作记录、资源检查、恢复和文本知识工具。它们适合处理陌生操作或恢复任务，不是已知 CST 操作的固定前置流程。直接控制会话存在时，服务会阻止混用大部分旧控制工具。

完整工具参数和行为见 [mcp/README.md](mcp/README.md)。

### Harness 与可选能力扩展

Harness 让执行过程可追踪：修改类操作先保存意图，再调用 CST，并保存实际结果。发生超时、连接丢失或结果记录不完整时，系统不会自动重放可能已经生效的操作。

当现有工具确实缺少某项 CST 能力时，可以查阅官方资料并编写参数化扩展。扩展首先作为不可调用的候选保存，只有经过人工审阅、明确授权、真实 CST 试调用和后置条件验证后，才注册为本地版本化能力。详细格式和安全要求见 [docs/api-development.md](docs/api-development.md)。

可选向量检索只用于从能力目录中发现相关工具。已知工具和精确 ID 的调用不依赖向量模型，仓库也不会自动安装依赖或下载模型。

### 多 agent 隔离测试

比较 Codex、Claude 等模型时，不要让它们共享会话状态和学习结果。每个 agent 应使用相同 Git commit，但拥有独立 worktree、MCP 进程、`design-records/`、CST 工程副本、CST 实例/PID，以及空白或相同快照的本地能力目录。任务、授权范围、工具配置和评分标准应保持一致。

如果机器只能运行一个 CST 实例，应串行测试，并在每次测试前恢复相同工程副本和空白运行记录。不要让两个 agent 同时控制同一个 CST PID。

### 注意事项

- 工程、输出、候选文件、记录目录和本地模型目录使用仓库相对路径。CST 安装位置只在运行时从环境解析。
- `mode="new"`、保存原工程、覆盖文件、求解、停止求解和执行本地扩展都需要明确意图或授权。
- 修改和保存是两个独立动作；工程清单、执行记录和能力注册记录都不是 `.cst` 工程备份。
- 求解器已提交、正在运行、已停止、成功计算、结果属于本次运行、结果物理有效是不同状态。
- 超时或 worker 异常后，CST 可能仍在运行，修改也可能已生效。先检查 CST 状态，再决定后续操作。
- 相同 `operation_id` 只返回已有凭据，不再次执行。
- Python 扩展不是安全沙箱，它拥有 MCP 服务进程的权限。只执行经过审阅和明确授权的源码。
- 不要同时使用 GUI、旧脚本和多个 agent 修改同一个工程。
- 修改仓库中的 Skill 不会自动更新以前复制到其他目录的 Skill；需要重新同步并重启 agent。
- 本次架构重整尚未通过新的真实 CST 集成测试，不应宣称所有 CST 版本和工程均已验证。

### 更多文档

- [MCP 使用与协议说明](mcp/README.md)
- [整体架构](docs/architecture.md)
- [扩展能力开发](docs/api-development.md)
- [CST 自动化 Skill](skills/cst-python-automation/SKILL.md)
- [环境变量示例](config/environment.example)

## English

### Overview

CST 2026 Skill + MCP combines the components required for agent-assisted CST Studio Suite automation:

- The **Skill** teaches an agent how to select tools, control risk, validate evidence, and recover from uncertain outcomes.
- The **MCP server** exposes a consistent CST toolset to Codex, Claude Code, and other MCP clients.
- The **CST execution layer** manages sessions, projects, parameters, solver jobs, and results.
- The **Harness** records intent and outcomes so uncertain mutations are not replayed automatically.
- Bundled **reference material** supports troubleshooting and extending missing capabilities.

The normal path is direct CST operation through MCP. API extension, textual memory, and vector discovery are optional facilities, not prerequisites for routine work.

### Capabilities and repository structure

The repository supports explicit CST sessions, existing project binding, parameter reads and updates, tracked solver jobs, and paged 0D/1D result access. Operations are plan-only by default, and uncertain mutations are never replayed automatically.

| Path | Responsibility |
| --- | --- |
| `skills/cst-python-automation/` | Agent workflow, safety rules, and CST-specific references |
| `mcp/` | stdio MCP entry point, protocol handling, adapters, compatibility entry points, and tests |
| `cst_api/` | CST sessions, projects, parameters, solvers, results, and extension execution |
| `harness/` | Execution journal, replay protection, workflow memory, and optional embedding adapter |
| `api_library/` | Capability catalog, candidate snapshots, version registration, and optional search |
| `shared/` | Relative-path validation, input schemas, atomic writes, and subprocess support |
| `config/` | Generic MCP, Codex, and environment examples |
| `docs/` | Architecture, extension development, and archived design material |
| `official-docs/`, `macro-library/`, `domain-guides/` | CST references, macro inventory, and domain guidance |
| `design-records/` | Local receipts, checkpoints, and verified extensions; ignored by default |

Engineering projects and experiment data can live in separate repository directories. Reusable definitions use repository-relative paths instead of machine-specific absolute paths.

### Requirements and setup

Requirements are Node.js 18+, a licensed CST Studio Suite 2026 installation, a Python interpreter compatible with the CST bindings, and a stdio MCP client.

Use [config/environment.example](config/environment.example) for environment settings, [config/mcp-client.example.json](config/mcp-client.example.json) for a generic client, and [config/codex.example.toml](config/codex.example.toml) for Codex. Claude Code and other clients use the same `node mcp/src/server.js` command while following their own configuration conventions.

Use the repository root as the service working directory. If the client cannot set it reliably, use `run-cst2026-mcp.cmd` on Windows or `run-cst2026-mcp.sh` on POSIX. The server communicates over stdio and is not an HTTP service.

Install [SKILL.md](skills/cst-python-automation/SKILL.md) through the client's Skill mechanism, or use it as project instructions, then restart the MCP connection.

### Typical workflow

1. Connect to an explicitly selected CST instance and retain the returned `session_id`.
2. Open or bind an existing repository-relative project and retain its `project_id`.
3. Inspect real parameters and state instead of guessing names or tree paths.
4. Save an authorized project copy before risky changes; parameter updates do not save automatically.
5. Start a solver only after user authorization, using `allow_solve=true`.
6. Poll the returned `job_id`; a stopped solver is not proof of a successful run.
7. Read an explicit result path and `run_id`, then assess freshness, units, and project provenance.
8. Save only as requested and disconnect. Disconnecting does not save, close CST, or stop a solver.

All direct CST tools default to `execute=false`. They return a plan until execution is explicitly enabled.

### Tools and profiles

The default `control` profile exposes 19 tools covering sessions, projects, parameters, solvers, results, capability discovery, and optional extension management. Set `CST_MCP_PROFILE=full` to additionally expose document/macro lookup, workflow records, resource checks, recovery, and textual-memory tools.

Compatibility tools help with unfamiliar or recovery work, but are not mandatory preparation for known CST operations. See [mcp/README.md](mcp/README.md) for the complete tool list and contracts.

### Harness and optional extension

The Harness stores intent before a mutation, dispatches it once, and records the actual outcome. A timeout, lost worker, or incomplete receipt does not trigger automatic replay.

When the built-in tools lack a CST capability, a reviewed implementation can be staged and trialed against CST. It becomes a versioned local capability only after explicit authorization and passing postcondition evidence. Details belong in [docs/api-development.md](docs/api-development.md).

Optional vector retrieval searches capability descriptions only. Known tools and exact IDs do not depend on an embedding model, and the repository never installs dependencies or downloads model weights automatically.

### Isolated agent evaluation

For fair Codex-versus-Claude comparisons, give each agent the same Git commit but isolate its worktree, MCP process, `design-records/`, CST project copy, CST instance/PID, and optional local capability index. Keep prompts, authorization, tool profile, and scoring criteria identical.

If only one CST instance can run, evaluate agents serially and restore the same project and record baseline before each run.

### Important notes

- Project, output, candidate, record, and local-model inputs use repository-relative paths.
- Creating an instance, saving the original, overwriting, solving, stopping a solver, and running an extension require explicit intent or authorization.
- Modification and saving are separate. A receipt or capability registration is not a `.cst` project backup.
- Solver submission, running state, termination, successful computation, result freshness, and physical validity are distinct claims.
- CST may continue after a timeout or worker failure. Inspect state before proceeding.
- Reusing an `operation_id` retrieves its receipt instead of executing again.
- Python extensions are not sandboxed. Run only reviewed and explicitly authorized source.
- Avoid concurrent GUI, legacy-script, and multi-agent edits to one project.
- Editing the repository Skill does not update copies installed elsewhere.
- The restructured architecture has not yet undergone a new live-CST integration run.

### Further documentation

- [MCP usage and contracts](mcp/README.md)
- [Architecture](docs/architecture.md)
- [Extension development](docs/api-development.md)
- [CST automation Skill](skills/cst-python-automation/SKILL.md)
- [Environment template](config/environment.example)
