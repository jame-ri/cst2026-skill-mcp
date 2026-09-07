# CST 自动化：中文使用指南

以 [主 SKILL](cst-python-automation/SKILL.md) 为唯一执行入口，安装时保留整个
cst-python-automation 目录及相对引用。本页只介绍用法，不单独维护一套规则。

- 普通资料问答按需查源，不强制走完整建模检查表。
- 建模与修改保留物理检查、参数化、History 和工程副本要求。
- 已明确授权的仿真在前置检查通过后执行；仅建模的请求不自动运行求解器。
- 阶段记录自动提取可复用流程和修复经验；缺少执行或验证证据的记录保持为候选。
- 后续任务先检索经验，再核对适用条件与当前工程状态，避免直接套用旧模型结论。

完整流程和记录示例见 [Harness](cst-python-automation/references/harness.md)。
物理检查见 [EM 门控](cst-python-automation/references/em-design-gates.md)。
路径与配置见 [环境说明](cst-python-automation/references/local-environment.md)。

Codex、Claude、Cursor 等 agent 使用同一个 MCP 实现，按实际暴露的工具名称调用。
连接同一仓库和知识目录时可共享经验；修改服务器代码或环境后需重启 MCP。

存储失败不等于 CST 操作失败。检查返回的 knowledge.status，必要时用
knowledge.capture_operation 补存已有记录，不重复执行已经成功的 CST 操作。
