# API development / 可复用 API 开发

## 1. 先复用 / Reuse first

已知内置 API 名称时直接调用 `cst.*` 或 `api.call`。不知道名称时用 `api.search`，再通过 `api.describe` 获取准确输入契约。只有目录确实缺少能力，才查看 `official-docs/`、CST History/VBA 示例及相关领域说明。

Call known APIs directly. Search discovers APIs, not necessarily documentation. Use official references only when a required capability is absent.

## 2. 候选定义 / Candidate definition

[示例 JSON](../api_library/examples/parameter-report.json) 和 [示例 Python](../api_library/examples/parameter-report.py) 展示只读参数报表。它们是待试用示例，不是已验证或已注册接口。

```json
{
  "id": "user.parameter_report",
  "version": "1.0.0",
  "description": "Read and independently re-check a live CST parameter report.",
  "effect": "read",
  "cst_version": "2026",
  "implementation": "api_library/examples/parameter-report.py",
  "entrypoint": "run",
  "verifier": "verify",
  "input_schema": {
    "type": "object",
    "properties": {
      "prefix": {"type": "string", "maxLength": 80}
    },
    "required": [],
    "additionalProperties": false
  },
  "references": [
    "official-docs/vba-3d/common_vbaapp/common_vbaappapplication_object.htm"
  ],
  "tags": ["parameters", "read"]
}
```

- ID 使用 `user.` 命名空间，版本使用 `major.minor.patch`，精确调用 ID 为 `id@version`。
- `effect` 为 `read`、`modify` 或 `solve`。它是声明，不是 Python 权限隔离。
- `cst_version` 是目标 CST 年份。worker 会检查实际版本；不能识别或不匹配时不执行扩展。
- `implementation` 与 `references` 是仓库内相对文件路径，不允许路径链接或越界。
- 源码上限 256 KiB，候选 JSON 上限 64 KiB；不要把大型数据或模型参数文件写入源码。
- 对象 schema 必须声明 `properties`、`additionalProperties=false`；支持基本类型、必填、枚举、字符串/数组长度、数值范围和字符串 pattern。不支持 `$ref`、`oneOf`、联合类型或其他未经实现的 JSON Schema 关键字。
- `default` 只是说明，不会自动填参；实现自行处理可选值。

Use a new version for changed code or contracts. A registered version cannot be silently overwritten by a different candidate.

## 3. 实现与验证 / Implementation and verification

```python
def run(context, arguments):
    # Perform one bounded, authorized operation.
    return {"data": context.parameters()}


def verify(context, arguments, result):
    # Re-observe a meaningful postcondition.
    observed = context.parameters()
    passed = observed == result["data"]
    return {
        "passed": passed,
        "summary": "Compared the returned data with a second live read.",
        "evidence": {"same_snapshot": passed, "count": len(observed)},
    }
```

`context` 提供：

| 成员 / Member | 含义 / Meaning |
| --- | --- |
| `project` | 当前绑定的 CST Project |
| `design_environment` | 当前明确选择的 CST 实例 |
| `project_path` | 当前工程的相对路径 |
| `path(relative_path)` | 安全解析仓库内路径；结果只在运行时使用，不写入可复用定义 |
| `parameters()` | 当前工程的实时参数快照 |
| `start_solver()` | 使用已有会话的跟踪式求解提交机制；仍需要求解授权 |

源码可使用官方 Python/History/VBA 接口，但不能硬编码机器路径。执行前会拒绝 Python 字符串常量中的绝对路径；这只是可移植性检查，**不是沙箱**。不要在 import 顶层执行 CST 操作；把操作放在入口函数。

Return bounded JSON-compatible data. The worker normalizes complex values as `{real, imag}`. Results are limited to 1 MiB and verification evidence to 64 KiB; large outputs should be paged or written as authorized relative-path artifacts.

验证必须返回 `passed=true`、非空 `summary` 和非空对象 `evidence`。对求解提交的检查只能说明提交状态，不能直接证明仿真收敛、结果新鲜或物理正确。自动入库信任这段已审阅的验证逻辑，不是第三方独立认证。

## 4. 保存候选 / Stage

MCP 调用：

```json
{
  "name": "api.stage",
  "arguments": {
    "candidate_path": "api_library/examples/parameter-report.json",
    "execute": true
  }
}
```

返回 `candidate_id`。系统保存源码和元数据快照，并记录参考文件摘要。这个步骤不运行 Python、不连接 CST、不创建可调用接口。

Without `execute=true`, staging only returns a plan. Staging is intentionally allowed while extension execution is disabled.

## 5. 受控试调用 / Authorized trial

先审阅源码，在服务环境中显式设置 `CST_ENABLE_API_EXTENSIONS=1`，并重启 MCP 服务。连接 CST、绑定工程后，使用真实返回的 ID 替换以下占位符：

```json
{
  "name": "api.trial",
  "arguments": {
    "candidate_id": "<api.stage 返回的 SHA-256>",
    "arguments": {
      "session_id": "<当前 session_id>",
      "project_id": "<当前 project_id>",
      "parameters": {"prefix": ""},
      "execute": true,
      "allow_extension_execution": true
    },
    "promote_on_pass": true
  }
}
```

求解类还需 `allow_solve=true`。未知结果不重跑；修改操作可能已部分生效。试验性修改应在用户授权的工程副本上进行。

The execution response and registration response are separate. Automatic registration requires all of the following:

1. The exact snapshotted source was executed successfully in the declared CST year.
2. The separate verifier returned passing postconditions with evidence.
3. The server saved an execution receipt bound to that candidate and implementation hash.
4. That API version is not occupied by different source, disputed or retired.

`promote_on_pass=false` 只试用不注册。失败不会入库。运行成功但凭据或注册写入失败时，保留实际执行结果并报告注册问题，不把 CST 操作执行第二遍。

## 6. 直接复用与停用 / Call and retire

```json
{
  "name": "api.call",
  "arguments": {
    "api_id": "user.parameter_report@1.0.0",
    "arguments": {
      "session_id": "<当前 session_id>",
      "project_id": "<当前 project_id>",
      "parameters": {},
      "execute": true,
      "allow_extension_execution": true
    }
  }
}
```

调用已注册接口仍保留源码摘要检查、版本检查和后置条件验证，不因为曾成功一次就取消保护。后续验证失败会标记 `disputed`；修复另建版本。

```json
{
  "name": "api.retire",
  "arguments": {
    "api_id": "user.parameter_report@1.0.0",
    "reason": "Replaced after reviewing a CST-version-specific behavior.",
    "execute": true
  }
}
```

Retirement preserves source and evidence. It does not delete files, modify the CST project or silently reactivate another version.

## 7. 可选语义发现 / Optional semantic discovery

Configure a trusted, complete local sentence-transformers model and an explicit model revision. The helper uses offline mode and `local_files_only=True`, with `trust_remote_code=False`; see the [official SentenceTransformer constructor documentation](https://sbert.net/docs/package_reference/sentence_transformer/model.html).

`api.reindex` explicitly embeds descriptions and schemas, not entire executable scripts. The current optional index supports up to 256 API descriptions per rebuild. Catalog or model-revision changes require rebuilding; exact-ID calls and keyword search remain independent of the model. Provisioning dependencies and model files is an operator action, never an automatic fallback.

## 验证范围 / Validation status

上述是已写入仓库的接口与开发约定，不代表示例或新实现已在真实 CST 上运行通过。本次重整未执行测试、仿真或嵌入模型下载。
