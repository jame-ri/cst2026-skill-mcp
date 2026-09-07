# Architecture / 架构

## 主链路 / Main path

```text
Agent + SKILL.md
    |
    v
MCP adapter (mcp/src/server.js, api-tools.js)
    |
    +--> direct cst.* tools ------+
    |                            |
    +--> api.call exact ID ------+--> CST controller
    |                                  |
    +--> api.search                     +--> harness execution journal
         keyword / optional vector      +--> persistent Python worker
                                                   |
                                                   v
                                            installed CST APIs
```

`cst.*` 与 `api.call` 共用同一个控制器，不维护两套会话。API 目录查找是精确注册表查询，不等于每次检索资料库。

Both direct tools and exact-ID calls share one controller and one worker. MCP describes and routes tools; it does not implement a second CST backend.

## 文件边界 / Ownership

| 层 / Layer | 文件 / Files | 负责 / Owns |
| --- | --- | --- |
| CST API | `cst_api/catalog.js` | 内置 API 名称与输入契约 |
| CST API | `cst_api/controller.js`, `worker-client.js` | 输入与执行门控、worker 生命周期 |
| CST API | `cst_api/worker.py`, `extensions.py`, `environment.py` | 真实 CST 调用、项目绑定、扩展执行、环境解析 |
| API library | `api_library/registry.js`, `storage.js`, `schema.js` | API 发现/调用、不可变候选、注册和生命周期 |
| API library | `api_library/vector-search.js` | 可选语义索引，不能替代可执行源码 |
| Harness | `harness/journal.js` | 执行前意图和执行后凭据；未知结果不重放 |
| Harness | `harness/knowledge-store.js` | 保留的文本流程经验，不是 API 源码注册表 |
| Harness | `harness/embeddings.py` | 显式配置的离线模型适配 |
| Shared | `shared/` | 相对路径、校验、原子写入、进程通信支持 |
| MCP | `mcp/src/mcp-protocol.js` | stdio JSON-RPC 消息与 MCP 响应 |
| MCP | `mcp/src/server.js`, `api-tools.js` | 工具发布、配置选择、适配与旧工具兼容 |

旧 `mcp/src/cst-*.js`、`mcp/src/knowledge-store.js`、`mcp/src/mcp-runtime.js` 和 `mcp/python/` 入口保留为薄兼容层。旧的一次性 Python 操作位于 `cst_api/legacy_ops.py`，不作为新会话式控制的主路径。

The legacy filenames remain thin compatibility entry points. Existing vendor documentation, guides and project directories are not renamed.

## 本地运行数据 / Local runtime data

```text
design-records/
  direct-operations/
    <operation-id>.json        # intent and actual outcome
  api-library/
    candidates/
      <candidate-sha256>/
        manifest.json         # immutable definition and reference hashes
        implementation.py     # immutable executable source
    registrations/
      <api-id-sha256>.json     # exact version -> candidate + passing receipt
    lifecycle/
      <api-id-sha256>.json     # disputed/retired history
    vectors/
      index.json              # rebuildable optional metadata index
    vector-runtime/           # short-lived embedding requests
  ...                         # existing engineering records and textual memory
```

API 库根目录可用 `CST_API_LIBRARY_DIR` 改为其他仓库内相对目录。自定义目录需由操作者自行加入忽略规则，避免将工程数据或生成代码意外提交。运行数据与源代码分开；“学到 API”默认只存本地，不自动提交或推送 Git。

A custom API store must remain repository-relative; add your own ignore rule if it lies outside the default ignored directory. Learning never commits or pushes generated code automatically.

## 生命周期 / Lifecycle

```text
source + candidate definition
    -> stage: candidate (not callable)
    -> authorized trial
        -> failed / uncertain: no registration
        -> passing verifier + durable receipt: locally_verified
    -> subsequent verification failure: disputed
    -> explicit retirement: retired
```

`locally_verified` 是一次具体调用、源码摘要、CST 年份与后置条件检查的记录，不是“所有模型通用”或“电磁验证通过”。`disputed` 与 `retired` 不自动恢复；新实现使用新版本。

The trial verifier is supplied with the implementation. It must re-observe meaningful state, not merely return success because no exception occurred. This is local evidence, not an independent security or physics certification.

## 执行一致性 / Execution semantics

- 默认 plan-only；试调用与真实读取均需明确执行。
- 修改类操作及所有 Python 扩展先落盘 intent，再调用 CST 一次。
- 成功返回后保存 outcome；落盘失败不能通过再执行 CST 来修补。
- `operation_id` 绑定参数摘要。相同 ID、相同请求返回历史凭据；不同请求拒绝。
- 有 intent 没有 outcome 时返回未知状态，不推断成功、不自动重跑。
- 本地文件锁只协调合作进程，不是分布式事务或 CST 回滚机制。
- worker 超时只终止辅助 Python 进程，不按名字批量结束 CST。
- 正常 EOF 尝试释放租约；强制退出不能保证清理。租约位于系统临时目录，按 CST PID 和 worker token 绑定。
- 只接受仓库内工程和产物路径。系统安装路径可在运行时解析；不要求 CST 原生 API 使用不支持的相对路径。

## 已知范围 / Current scope

The default MCP profile exposes only the direct control and API-library adapters. The `full` profile also exposes the retained legacy tools; the main server still contains legacy dispatch for compatibility.

The current architecture is intentionally not a complete translation of every vendor API. New geometry, materials, ports, boundary conditions, solver configuration and additional result types should enter through reviewed, versioned APIs rather than an unrestricted public `eval` tool.

This implementation has not undergone a new test run or live CST validation during the restructure.
