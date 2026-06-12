# 天线结果诊断和下一步结构修改规则

## 目标

本指南用于把 CST 结果转化为下一轮结构修改假设。模型不能只说“结果不好”，必须指出问题、证据、可能物理原因、建议的几何或参数变异、预期改善和风险。

## 诊断输入

优先收集：

- `S11`、`S21`、多端口隔离、VSWR。
- -10 dB 或用户指定阈值带宽。
- 目标频段内增益、效率、方向图、3 dB 波束宽度、前后比、副瓣。
- 极化、轴比、交叉极化。
- 电流分布、近场、远场监视器。
- Mesh、端口模式、边界距离、仿真日志。

先确认指标来源和频率点，避免把不同 monitor 或不同版本的结果混用。

## 匹配问题

### 谐振频率偏高

可能原因：

- 有效电流路径太短。
- 等效电容不足或耦合不足。
- 介质/空气层假设不对。

候选修改：

- 加长主辐射路径、加槽、加蛇形、加枝节。
- 增加耦合长度或寄生单元。
- 增加局部电容加载或调整馈电位置。

风险：

- 尺寸变大或效率降低。
- 新模式可能影响方向图。

### 谐振频率偏低

候选修改：

- 缩短电流路径。
- 减小槽长或枝节长度。
- 降低耦合或电容加载。
- 调整馈点到阻抗更合适区域。

### S11 深度不够但频点接近

候选修改：

- 调馈点位置、馈线宽度、馈电间隙、匹配枝节。
- 微调耦合间距。
- 保持主辐射长度，优先改阻抗匹配结构。

### 带宽太窄

候选修改：

- 引入邻近谐振：寄生单元、槽、叠层、耦合枝节。
- 增大有效厚度或空气层。
- 改馈电耦合方式。
- 对多谐振结构优化谐振间距。

风险：

- 额外谐振可能造成方向图或效率下降。

## 增益和效率问题

### 增益低但效率高

可能原因：

- 孔径小、方向图太宽、阵列口径不足。
- 能量辐射方向不符合目标。

候选修改：

- 增大有效孔径。
- 加反射结构、寄生导向结构、超表面或阵列单元。
- 调整地板/反射面尺寸。

### 效率低

可能原因：

- 金属/介质损耗高。
- 强电流集中在窄槽、薄线、损耗介质或匹配网络。
- 小型化过强。

候选修改：

- 减少窄缝和高电流瓶颈。
- 选低损耗材料或降低损耗区域电场。
- 放宽小型化，减少过度加载。

### 方向图异常

候选修改：

- 检查边界和空气盒距离。
- 检查端口模式和参考面。
- 调整地板、寄生结构或阵列相位。
- 检查结构是否不对称导致交叉极化升高。

## 多端口和阵列问题

### 隔离差

候选修改：

- 加去耦枝节、地板槽、寄生隔离结构、EBG/超表面结构。
- 调整单元间距和极化方向。
- 检查馈电网络耦合。

### 扫描或波束问题

候选修改：

- 检查阵列间距是否引入栅瓣。
- 调整幅相加权。
- 检查边缘单元和周期边界设置。

## 仿真设置诊断

先排除这些非结构问题：

- 端口没有正确接触导体。
- 边界离天线太近。
- Farfield monitor 频点不在目标频点。
- Mesh 太粗导致 S 参数或效率不稳定。
- 结果来自旧设计版本。
- 工程没有 rebuild 或参数未生效。

## 下一步建议格式

```yaml
diagnosis:
  issue: resonance_high | poor_matching | narrow_bandwidth | low_gain | low_efficiency | bad_pattern | poor_isolation
  evidence: metrics and source paths
  likely_causes: ranked physical causes
proposed_mutation:
  mutation_id: next mutation id
  parent_design_id: current design id
  operation: add_slot | adjust_feed | add_parasitic | edit_ground | add_via | parameter_tune
  target_objects: CST object names
  parameters: proposed values or bounds
  expected_effect: what should improve
  risks: possible tradeoffs
validation:
  required_results: S11, farfield, efficiency, logs
  accept_rule: objective threshold
  rollback_rule: when to reject
```

## 不能做的事

- 不要只根据一个 S11 曲线就断言最终天线好坏。
- 不要忽略效率、方向图、端口和边界设置。
- 不要把旧版本结果当作新结构结果。
- 不要在没有指标来源时报告“优化成功”。
- 不要把多目标问题简化成单个 S11 最小值。
