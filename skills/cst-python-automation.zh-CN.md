---
name: cst-python-automation
description: "当用户提出 CST Studio Suite / CST-MWS 自动化、.cst 工程、CST 天线/RF 建模、参数/几何/材料/端口/边界/求解器设置、CST 结果树/日志/S11/S21/远场/增益/效率读取、CST 宏/History/VBA 示例、优化/扫参/代理模型/机器学习数据流相关需求时使用。若只是一般天线/RF 理论、普通 S 参数绘图、非 CST 仿真问题，不要触发，除非用户明确要求 CST 工程或结果自动化。"
---

# CST Python 自动化 Skill

## 核心分工

本 skill 负责模型行为：如何理解用户的 CST 需求，如何先问清物理结构，如何使用官方资料和宏库，如何避免误建模，如何做进程/资源/弹窗防护，以及如何记录设计版本和结果。

本仓库（`$CST_API_ROOT` 或仓库根目录）提供标准工具层：CST 官方文档搜索、安装宏库搜索、History/VBA 片段提取、设计记录、CST Python helper、进程预检、恢复和关闭策略。配置路径前先读 `skills/cst-python-automation/references/local-environment.md`。

优先使用 MCP 工具；MCP 覆盖不足时，再按本 skill 规则直接读仓库资料并写 CST Python / VBA / History 脚本。

## 适用范围

用于以下 CST Studio Suite 工作流：

- 启动 CST、连接现有会话、复用已打开工程、打开 `.cst` 工程
- 修改参数、材料、几何、端口、边界、监视器、网格、求解器设置
- 从 CST 安装宏中学习 `VBA/History/add_to_history` 命令模式
- 读取 `S11`、`S21`、远场、增益、效率、电流、结果树、日志
- 重建、求解、后处理、导出结果
- 复杂天线或 RF 结构的版本化迭代
- 优化、参数扫描、代理模型、机器学习数据生成

## 触发方式

强触发：

- `CST`、`CST Studio Suite`、`CST-MWS`
- `.cst`、打开工程、启动 CST、连接 CST、结果树
- CST 上下文中的 `macro`、`VBA`、`History`、`RunScript`、`add_to_history`
- CST 工程的几何、端口、边界、材料、求解、结果读取

上下文触发，只有在用户明确或隐含 CST 时使用：

- 天线、RF、微波、`S11`、`S21`、远场、增益、效率
- 参数扫描、优化、代理模型、机器学习数据

## 工具优先级

1. 有 `cst2026-mcp` 时，优先用 MCP 标准工具。
2. 宏库相关用 `docs.search_macros`、`docs.read_macro`、`history.extract_pattern`。
3. 官方资料相关用 `docs.search_official_docs`、`docs.read_official_doc`。
4. 设计版本记录用 `records.create_variant`、`records.append_operation`。
5. 建模、求解、解释结果前，用 `cst.inspect_project`、`cst.inspect_geometry`、`cst.inspect_physics_setup`、`cst.result_sanity` 做只读检查。
6. 长任务、扫参、优化前，用 `cst.process_status`、`cst.preflight_resources`、`cst.job_checkpoint`、`cst.recover_job`、`cst.cleanup_stale_processes` 防止进程卡死、内存不足和中断后无法恢复。
7. 受控启动、关闭、实时参数修改用 `cst.closed_start`、`cst.close_project`、`cst.live_modify_parameter`。这些工具默认 `execute=false`，只有用户意图明确时才执行。
8. 重新发现 CST 路径前，先查 `CST_PYTHON_EXE`、`CST_API_ROOT`、`CST_MCP_ROOT`、`CST_OFFICIAL_DOCS`、`CST_MACRO_LIBRARY` 和本地环境缓存。

Codex 中可能暴露为下划线名称：

| README/MCP 名称 | Codex 可调用名 |
| --- | --- |
| `docs.search_macros` | `docs_search_macros` |
| `docs.read_macro` | `docs_read_macro` |
| `docs.search_official_docs` | `docs_search_official_docs` |
| `docs.read_official_doc` | `docs_read_official_doc` |
| `history.extract_pattern` | `history_extract_pattern` |
| `records.create_variant` | `records_create_variant` |
| `records.append_operation` | `records_append_operation` |
| `cst.inspect_project` | `cst_inspect_project` |
| `cst.inspect_geometry` | `cst_inspect_geometry` |
| `cst.inspect_physics_setup` | `cst_inspect_physics_setup` |
| `cst.result_sanity` | `cst_result_sanity` |
| `cst.process_status` | `cst_process_status` |
| `cst.preflight_resources` | `cst_preflight_resources` |
| `cst.job_checkpoint` | `cst_job_checkpoint` |
| `cst.recover_job` | `cst_recover_job` |
| `cst.cleanup_stale_processes` | `cst_cleanup_stale_processes` |
| `cst.closed_start` | `cst_closed_start` |
| `cst.close_project` | `cst_close_project` |
| `cst.live_modify_parameter` | `cst_live_modify_parameter` |

## 资料优先级

按需读取：

1. `skills/cst-python-automation/references/local-environment.md`
2. `$env:CST_MCP_ROOT\README.md`
3. `$env:CST_OFFICIAL_DOCS\python\`
4. `$env:CST_OFFICIAL_DOCS\python_cst_libraries\cst\`
5. `$env:CST_OFFICIAL_DOCS\vba-3d\`
6. `$env:CST_OFFICIAL_DOCS\vba-des\`
7. `$env:CST_OFFICIAL_DOCS\advanced\`
8. `$env:CST_MACRO_LIBRARY\macro-inventory.csv`
9. `$env:CST_MACRO_LIBRARY\cst-macro-usage.zh-CN.md`
10. `$env:CST_MACRO_LIBRARY\macro-catalog.zh-CN.md`
11. `$env:CST_API_ROOT\domain-guides\design-evolution.zh-CN.md`
12. `$env:CST_API_ROOT\domain-guides\geometry-mutation.zh-CN.md`
13. `$env:CST_API_ROOT\domain-guides\result-diagnosis.zh-CN.md`
14. `$env:CST_API_ROOT\domain-guides\optimization-ml-data.zh-CN.md`

## 使用规则

1. 修改前先检查当前工程、参数、结果树或已有设计记录。
2. 优先依据 CST 官方文档、安装宏和仓库示例，不凭空猜 API。
3. 在线会话用 `cst.interface`，已保存结果读取用 `cst.results`。
4. 几何、端口、边界、网格、求解器设置优先用 `model3d.add_to_history()`。
5. 使用缓存的 `CST_PYTHON_EXE` 运行 CST Python。路径失败时只做任务内修正；除非用户明确要求，不改持久环境变量。
6. 不熟悉的 VBA/History 命令先查宏库，提取最小可控片段，不把完整交互宏当黑盒批量运行。
7. 默认不保存原工程。破坏性修改、结构删除、长仿真、优化循环使用工程副本或 job copy。
8. 复杂结构演化记录 `design_id`、`parent_design_id`、操作、指标、日志、数据集版本、代理模型版本。
9. 只使用官方文档、安装宏或仓库代码确认过的 API、方法名、参数名。
10. API 细节不确定时先验证，不用猜测补全。
11. 使用有界的 inspect-mutate-verify-checkpoint 循环；避免一次脚本完成建模、物理设置、求解和解释。
12. 长求解、扫参、优化、机器学习数据生成前做资源预检、记录 checkpoint、规划恢复。
13. CST GUI 模态弹窗视为自动化阻塞。启动前用 `cst.process_status` / `cst.preflight_resources` 检查。若 Update Manager 报 `License details are required to check for updates`，识别为 CST 自动更新/许可证配置问题，而不是建模错误。
14. 不依赖 `DesignEnvironment.close()` 决定未保存工程如何关闭。helper 自己新建或临时打开的工程必须先显式执行关闭策略：`no_save` 调 `Project.close()`；`save_copy` 调 `Project.save(copy_path, ...)` 再 `Project.close()`；`save_original` 只允许已有保存路径的工程。所有 helper-owned 工程关闭后，才允许关闭 DesignEnvironment。

## 弹窗和关闭策略

CST 自动化必须能在没有人工点击弹窗的情况下收尾。

- Update Manager 启动弹窗：若看到 `License details are required to check for updates`，报告为 CST 自动更新/许可证配置弹窗。不要把它误判为建模失败。建议用户在 CST `File > Options > Preferences` 关闭 automatic software updates，或修复 Update Manager 的 license 设置。
- 保存确认弹窗：避免 `Do you want to save changes to 'Untitled_0.cst'?`。helper-owned 临时工程用 `Project.close()` 明确不保存；需要保留成果时先 `Project.save(path, include_results, allow_overwrite)`，再 `Project.close()`。
- 新工程规则：脚本调用 `new_mws()` 或创建 untitled 工程后，必须在 `finally` 中保存到明确 `.cst` 路径或用 `Project.close()` 关闭。材料探测、几何探测、失败建模都不能留下 untitled 工程。
- 用户已有工程规则：除非用户明确要求，不关闭、不保存用户打开的工程。生成变体优先 `save_copy`；只读检查和可恢复测试用 `no_save`。
- 关闭顺序：先 project，后 DesignEnvironment。不要在未保存 helper-owned 工程仍打开时调用 `de.close()`。
- 如果弹窗已经阻塞，停止当前 CST 阶段，报告已知弹窗文本，等待用户 UI 操作或走明确 PID 清理流程。不要按进程名杀 CST。

## 需求澄清门

当用户要求创建、修改、求解、优化或诊断 CST 模型时，先规范需求，再建模或求解。

若用户没有说明，优先问简短问题确认：

- 任务类型：新建、修改、检查/调试、求解、读结果、优化、生成数据集
- 工程来源：已有 `.cst` 路径、模板/复制策略、还是新建工程
- 物理结构：拓扑、坐标系、单位、尺寸、层叠、材料、导体、馈电、端口、边界、频段、目标指标
- 建模范围：哪些必须建，哪些可简化，哪些数值可假设
- 自动化模式：`full_auto` 全自动，或 `review_gated` 在仿真前让用户确认
- 输出期望：CST 工程、图、指标、manifest、导出数据、诊断文字

默认使用 `review_gated`，除非用户明确要求全自动/无人值守。建模或求解前记录 `automation_mode` 和关键假设。

`review_gated` 模式下，几何建完、端口加完后，不立即求解。先给用户一个审查包：结构简述、材料、对象/组件树证据、端口类型和位置、边界/求解计划、假设、未检查项。用户确认后才运行仿真。

`full_auto` 模式仍必须执行物理结构门、几何不变量、材料/边界/求解门、结果 sanity gate，并记录所有假设。

## 物理结构门

在理解物理结构到足以写出紧凑结构 brief 前，不创建或修改几何、端口、边界、材料、网格、求解器。

建模或修改非平凡结构前，必须说明或记录：

- 物理问题和目标观测量，例如 `S11`、增益、效率、场分布、特征模
- 坐标系、单位、频段、传播或辐射方向
- 层叠或 3D 拓扑：基板、金属层、空气/真空区、腔体、via/pin、馈线、连接器、屏蔽、孔径、缝隙、地
- 每个物理区域的材料，并区分已知值和假设值
- 电连接关系：哪些导体接触，哪些隔离，哪些为地/参考，哪些有意悬浮
- 馈电拓扑：信号导体、返回/屏蔽/地导体、馈电介质、端口截面或端子点、分布式还是集总激励
- 边界物理含义：开放/辐射、电/磁对称、周期/Floquet、PEC/PMC 墙、波导孔径
- 用户提供的尺寸和推断尺寸

缺失信息会影响拓扑、材料、电连接、激励、边界或结果解释时，必须追问、检查工程或查参考资料。不要仅凭天线名称、论文标题或常见模板推断物理部件，除非假设已记录且对任务无害。

## 几何不变量

创建或修改几何后，在加端口或求解前检查：

- 预期实体、薄片、组件、材料都存在且命名明确
- bounding box、层高、基板厚度、导体厚度、间隙、槽宽符合结构 brief
- 布尔、pick、变换、镜像、阵列没有误删、误合并、反转或脱离对象
- 应接触的导体真实接触或重叠；应隔离的导体有非零间隙
- 馈电需要的地/参考导体存在且连续
- via、pin、probe、shield、feed line 连接正确层，不短路不该连接的金属
- 介质区域包围预期馈电/场区，未覆盖金属体积
- airbox、端口、边界面在正确截面外或截面上，不穿过有源结构，除非刻意这样建
- 对称或周期切割对真实几何和激励相位有效

若某项无法从 CST 状态检查，明确标记风险，不把仿真结果解释为物理已验证。

## 材料、边界和求解门

求解前确认材料、边界、网格、监视器、求解器匹配物理结构 brief。

求解前检查：

- 每个非真空区域有预期材料、单位、导电率或损耗模型、介电常数/磁导率、频率依赖；未知材料保持显式假设
- 金属模型正确：PEC、有限导电率、lossy metal、thin sheet、surface impedance、导入材料
- 背景、airbox、开放/PML/辐射距离与频段、辐射体或波导尺寸一致
- 边界表达真实物理：天线用 open/radiation；PEC/PMC/symmetry 只在场和激励满足对称时用；periodic/Floquet 只用于有效单元相位条件
- 求解器匹配问题：时域、频域、特征模、积分方程、周期/Floquet、线缆、协同仿真
- 频率范围、激励带宽、监视器、远场设置、S 参数归一化、端口模式数足够支持目标指标
- 网格解析最小关键特征：缝隙、槽、导体厚度、via/pin 半径、馈电介质、端口截面、趋肤深度、高场角点
- 细小几何主导结果时，说明局部网格加密或自适应收敛标准

若求解器、边界、材料、网格只是“方便默认”，而非物理正确，必须先停下。使用默认值时记录为什么默认值对该结构成立。

## 参数化规则

- History 命令引用参数前先创建 CST 参数。顺序：单位、`StoreParameter` / `StoreParameterWithDescription`、频率范围、材料、几何、端口、网格、监视器、求解器。
- 所有用户可调值都进参数表：基板厚度、材料常数、patch 尺寸、slot 尺寸、via/pin 半径、馈电/同轴尺寸、阵列周期、单元数、求解频段。
- 用户希望手动编辑的值，用参数名和 CST 表达式，不把 Python 计算后的数值硬编码进 `.Xrange`、`.Yrange`、`.Zrange`、`.Radius`、材料 epsilon/tanD 或求解频率。
- 复用的派生坐标或层级也存参数，例如 `z_top_min`、`z_top_max`、`x_e1`、`x_e2`。

## 端口设置规则

- 定义端口前，先分类馈电和导体：馈电类型、信号导体、参考导体/屏蔽、介质、端口截面、目标模式、分布式或集总。
- 根据物理馈电选 CST 端口对象，不按方便程度选择。常见对象：`Port`、`DiscretePort`、`DiscreteFacePort`、`CablePort`。
- 同轴、SMPM、probe 且有内导体/介质/外导体或屏蔽：优先 waveguide `Port`，建好内导体、介质、外导体/屏蔽和地间隙后，在同轴截面 pick face 创建端口。
- 矩形/圆波导、喇叭 throat、波导 launcher：在端口波导孔径用 waveguide `Port`。
- SIW：在 SIW 截面用 waveguide `Port`，先建上下金属、基板、via fence 和孔径面。
- 微带、CPW、stripline、接地共面馈线：分布式线激励优先横向截面的 waveguide `Port`，包含信号线、介质和参考地，必要时加 mode line。
- 两端子小间隙、局部 pin 到地、点到点激励：用 `DiscretePort`，并记录这是集总近似。
- 面集总激励：仅在物理确实需要且 CST Help 确认求解器支持时用 `DiscreteFacePort`。
- 线缆模型工作流：只在 CST cable 对象/线缆流程中用 `CablePort`，不要当通用同轴端口替代。
- 周期单元或平面波：用 Floquet port 或 `PlaneWave`，不要用普通 lumped feed。
- 对 waveguide-style port，优先 UI 等价的 pick-face 流程：清 pick、pick 端口面、`With Port` `.Coordinates "Picks"` `.Create`。
- 不要把分布式馈电失败静默降级成 `DiscretePort`。端口创建失败时，检查 pick face 和 history 命令，修复物理端口定义。
- 在 build summary 记录：`feed_type`、CST 端口对象、信号/参考导体、pick face 或坐标、mode line、参考资料来源。

## 决策流程

- Intake：澄清建模需求、工程来源、输出期望、`automation_mode`；默认 `review_gated`。
- Connect/open CST：长任务先 `cst.process_status` 和 `cst.preflight_resources`；列出现有会话和已打开工程；只读发现用 `cst.inspect_project`。
- Modify parameters：读原值、写测试值、rebuild、必要时暂停观察、默认恢复、不保存。
- Modify geometry：通过物理结构门；已有工程先 `cst.inspect_geometry`；创建设计记录；说明假设；执行最小 History 修改。
- Add/delete structures：说明目标对象、材料、坐标系、物理连接、布尔操作、回滚策略。
- Review gate：`review_gated` 下，几何和端口完成后、仿真前给审查包并等待用户确认。
- Assign materials/boundaries/solver：通过材料、边界和求解门，必要时用 `cst.inspect_physics_setup`。
- Read results：先发现结果树路径，再读 S 参数、远场、效率、增益、日志；解释前用 `cst.result_sanity`。
- Optimize/ML：把 CST 作为昂贵真实求解器，记录每次 trial 的输入、输出、工程副本、日志、数据版本。
- Finalize：结束前执行声明的保存/关闭策略。helper-owned 临时工程先 `Project.close()` 或保存到明确副本路径，再关 DesignEnvironment。

## 长任务可靠性

长求解、扫参、优化、可能跨越当前 Codex turn 的任务必须可恢复。

执行前：

- 用 `cst.process_status` 和 `cst.preflight_resources` 检查 CST 进程、内存、磁盘。
- 检查 preflight 的 Update Manager warning。若自动更新/许可证弹窗可能出现，记录 warning，不把启动中断当建模失败。
- 用 `cst.job_checkpoint` 记录 `preflight` checkpoint。
- 优先使用工程副本或 job copy，不依赖未保存 GUI 状态恢复。
- 预定义阶段名：`preflight`、`structure_inspect`、`geometry_mutation`、`geometry_verify`、`physics_setup`、`solve`、`result_read`、`sanity`、`finalize`。

执行中：

- 每个昂贵或脆弱阶段前后记录 `running` / `done` checkpoint。
- 求解设置 timeout，并在阶段之间监控进程和资源。
- 阶段卡住时标为 `interrupted` 或 `failed`，不要不检查状态就重跑破坏性阶段。
- preflight 报告 CST 进程过多或内存不足时，不再启动新 CST。
- 脚本 `finally` 中先关闭 helper-owned 工程，再关闭 DesignEnvironment。

恢复：

- 用 `cst.recover_job` 找最后完成 checkpoint 和安全恢复点。
- 用 `cst.process_status` 判断 CST 进程仍可用、卡住或 stale。
- `cst.cleanup_stale_processes` 只能用明确 PID 且 `allow_terminate=true`；不要按名字杀 CST。
- 恢复后重新运行相应 inspect 或 sanity gate，再解释结果。

## 结果 Sanity Gate

把 CST 输出作为工程结论前，先检查物理和数值可信度。

S 参数和端口结果：

- 结果树路径存在且对应预期激励和模式
- 端口模式名、参考阻抗、重归一化、去嵌入、校准面已知或作为假设报告
- 被动结构不应出现不可能增益，例如 `|S11| > 0 dB` 或非物理 S 参数幅值，除非主动/非标准归一化明确存在
- 结构应满足互易、对称或隔离预期时要检查

远场、增益、效率：

- farfield monitor 频率匹配设计频率或目标频段
- accepted power、radiated power、total efficiency、realized gain、directivity 相互合理
- 主瓣方向、极化、零陷符合结构和馈电方向
- 说明报告的是 gain、realized gain 还是 directivity

求解健康：

- CST messages/logs 没有未解决的端口、网格、材料、边界、收敛、许可证 warning
- 自适应收敛或网格加密达到目标；未收敛必须报告
- 参数或几何修改后的结果尽量与上一设计比较

sanity check 失败或无法执行时，把数值报告为未验证数据，而不是物理结论。

## 输出契约

修改工程、运行/计划 CST 执行、创建设计记录、读取仿真结果或生成产物时，最后给出紧凑记录：

```yaml
project_path: 使用或生成的 CST 工程
save_policy: no_save | save_copy | save_original
design_id: 当前结构版本
parent_design_id: 上一结构版本或 null
automation_mode: full_auto | review_gated
user_confirmation: required, received, skipped_full_auto, or not_applicable
physical_structure: 建模前检查过的拓扑、馈电、材料、边界、假设
physics_setup: 求解前检查过的材料、边界、网格、监视器、求解器
mcp_tools: 本次调用的 MCP 工具
operations: 参数/建模/仿真/结果读取步骤
metrics: 提取指标及来源路径
sanity_checks: 结果树、端口、远场、效率、收敛、日志检查
job_status: 当前可恢复任务状态
checkpoints: preflight/running/done/failed/interrupted/recovered 阶段记录
resource_guard: 进程、内存、磁盘、timeout、清理检查
modal_dialogs: Update Manager warning、已避免的保存弹窗、遇到的阻塞弹窗
close_policy: 结束 CST 自动化前执行的 project close/save 动作
recovery: 最后完成 checkpoint 和恢复建议
logs: Model.log/output.json/outputDS.json 路径
artifacts: 生成文件、数据集、图、manifest、model card
versions: dataset_version, surrogate_version, CST project copy version
source_macros: 参考或改写的 CST 安装宏路径
warnings: 假设、跳过项、风险
errors: 失败与恢复尝试
```

纯建议或小型 CST 参考问题可简短回答，不强制完整 YAML；但要说明决策、查过的 CST 来源和不确定性。
