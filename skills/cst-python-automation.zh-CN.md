---
name: cst-python-automation
description: 当用户询问 CST Studio Suite、CST-MWS、天线或 RF 仿真、打开或启动 .cst 工程、修改参数或几何、定义端口或边界、运行求解器、读取 S11/S21/远场/增益/效率/日志、使用 CST 安装宏示例、或构建优化/机器学习驱动的 CST 工作流时使用。
---

# CST Python 自动化 Skill

## 核心分工

这个 skill 负责模型行为规则：如何理解自然语言请求、如何保证安全、如何查官方资料、如何记录设计版本、如何汇报结果。

`D:\CSTapi\mcp\` 负责标准化工具调用：搜索宏库、读取官方文档、提取 History/VBA 片段、创建设计记录、以及通过 CST Python helper 执行受控动作。

优先使用 MCP 工具完成可标准化动作；当 MCP 工具不够时，再按本 skill 的规则直接查资料和编写脚本。

## 适用范围

用于以下 CST Studio Suite 场景：

- 启动 CST、连接正在运行的会话、复用已打开工程、或打开 `.cst` 工程
- 修改参数、材料、几何、端口、边界、监视器、网格、求解器设置
- 从安装宏中学习 `VBA/History/add_to_history` 命令模式
- 读取 `S11`、`S21`、远场、增益、效率、电流、结果树、日志
- 重建、求解、后处理、导出结果
- 迭代复杂天线或 RF 结构，记录设计谱系
- 运行优化闭环、参数扫描、代理模型或深度学习数据闭环

## 触发词

用户提到以下内容时，优先使用此 skill：

- `CST`、`CST Studio Suite`、`CST-MWS`
- `antenna`、`RF`、`microwave`、`S11`、`farfield`、`gain`、`efficiency`
- `parameter sweep`、`optimization`、`surrogate`、`ML`、`deep learning`
- `macro`、`VBA`、`History`、`RunScript`、`add_to_history`
- `open .cst`、`launch CST`、`connect CST`、`modify geometry`

## 工具优先级

1. 如已安装 `cst2026-mcp`，优先用 MCP 工具执行标准动作。
2. 查宏库用 `docs.search_macros`、`docs.read_macro`、`history.extract_pattern`。
3. 查官方文档用 `docs.search_official_docs`、`docs.read_official_doc`。
4. 建立设计记录用 `records.create_variant`、`records.append_operation`。
5. 受控启动或实时改参用 `cst.closed_start`、`cst.live_modify_parameter`；默认 `execute=false`，只有用户意图明确时才执行。
6. 若 MCP 不可用，直接读取仓库内资料并编写 Python/VBA/History 脚本。

## 资料优先级

按需读取这些资料：

1. `D:\CSTapi\mcp\README.md`
2. `D:\CSTapi\official-docs\python\`
3. `D:\CSTapi\official-docs\python_cst_libraries\cst\`
4. `D:\CSTapi\official-docs\vba-3d\`
5. `D:\CSTapi\official-docs\vba-des\`
6. `D:\CSTapi\official-docs\advanced\`
7. `D:\CSTapi\macro-library\macro-inventory.csv`
8. `D:\CSTapi\macro-library\cst-macro-usage.zh-CN.md`
9. `D:\CSTapi\macro-library\macro-catalog.zh-CN.md`
10. `D:\CSTapi\domain-guides\design-evolution.zh-CN.md`
11. `D:\CSTapi\domain-guides\geometry-mutation.zh-CN.md`
12. `D:\CSTapi\domain-guides\result-diagnosis.zh-CN.md`
13. `D:\CSTapi\domain-guides\optimization-ml-data.zh-CN.md`

## 使用规则

1. 先检查当前工程、参数、结果树或已有记录，再提出修改。
2. 优先依据官方文档、安装宏、仓库示例，不要凭空猜 CST API。
3. 在线会话用 `cst.interface`，离线读取保存结果用 `cst.results`。
4. 几何、端口、边界、网格、求解器设置优先通过 `model3d.add_to_history()` 注入。
5. 不熟悉的 CST VBA/History 命令先查宏库，提取最小可控片段，不把完整交互式宏当黑盒批量运行。
6. 默认不保存原工程；破坏性修改、删结构、长仿真、优化循环先复制工程或创建 job copy。
7. 复杂结构演化必须记录 `design_id`、`parent_design_id`、操作、指标、日志、数据版本、代理模型版本。
8. 只使用已被官方文档、安装宏、或本仓库代码确认的 API、方法名和参数名。
9. API 细节不确定时先核实，不用猜测补全。

## 决策流程

- 连接/打开 CST：先列出现有会话和已打开工程；需要冷启动时用 MCP 的 `cst.closed_start` 或等价脚本。
- 修改参数：先读原值，再写入测试值，rebuild，必要时暂停观察，默认恢复且不保存。
- 修改结构：先建立设计记录，说明变更假设，再用最小 History 片段修改几何。
- 增减结构：明确新增/删除对象、材料、坐标系、布尔操作和可回滚策略。
- 读取结果：先发现结果树路径，再读 S 参数、远场、效率、增益、日志等指标。
- 优化/深度学习：把 CST 当昂贵真实求解器，每次 trial 都记录输入、输出、工程副本、日志和数据版本。

## 输出契约

任务结束时尽量报告：

```yaml
project_path: 使用或生成的 CST 工程
save_policy: no_save | save_copy | save_original
design_id: 当前结构版本
parent_design_id: 上一结构版本或 null
mcp_tools: 本次调用的 MCP 工具
operations: 参数/建模/仿真/结果读取步骤
metrics: 提取指标及来源路径
logs: Model.log/output.json/outputDS.json 路径
artifacts: 生成文件、数据集、图、清单、模型卡
versions: dataset_version、surrogate_version、CST project copy version
source_macros: 参考或改写的 CST 安装宏路径
warnings: 假设、跳过项、风险
errors: 失败与恢复尝试
```
