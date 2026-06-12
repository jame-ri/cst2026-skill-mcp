# 复杂天线结构演化设计指南

## 目标

本指南用于让模型把天线设计理解为“结构版本演化”，而不是套用偶极子、贴片、喇叭等简单模板。实际任务中，模型应读取当前 CST 工程，诊断指标，提出结构变异，在副本中增删改几何，仿真评估，再记录下一轮假设和结果。

## 核心原则

- 不要先假设天线类型。先从 CST 工程读取结构树、组件、材料、端口、边界、监视器、参数表和已有结果。
- 每轮设计都是一个版本：`parent_design_id -> mutation_id -> child_design_id`。
- 每次变异都必须说明假设：改哪里、为什么改、预期改善哪个指标、可能牺牲什么。
- 默认在 job copy 中修改，不保存原工程。
- 对复杂结构优先使用小步变异，不要一次性大改多个耦合因素。
- 不确定几何含义时，先列出结构和命名，再提出低风险候选修改。

## 结构版本命名

推荐目录：

```text
runs/
  antenna-task-YYYYMMDD-HHMMSS/
    manifest.json
    trials.jsonl
    designs/
      D0000_baseline/
        project.cst
        design.json
        metrics.json
      D0001_add_slot_near_feed/
        project.cst
        design.json
        metrics.json
```

推荐 ID：

- `task_id`: 一次用户任务或优化任务的全局 ID。
- `design_id`: `D0000`, `D0001`, `D0002`。
- `parent_design_id`: 来源设计，基线为 `null`。
- `mutation_id`: `M0001_add_slot_near_feed`。
- `project_version`: CST 工程版本，和 `design_id` 一一对应。
- `data_version`: 数据集版本，例如 `dataset_v003`。
- `surrogate_version`: 代理模型版本，例如 `surrogate_v002`.

## 每轮设计记录

每个 `design.json` 至少包含：

```json
{
  "task_id": "antenna-task-20260602-153000",
  "design_id": "D0001",
  "parent_design_id": "D0000",
  "mutation_id": "M0001_add_slot_near_feed",
  "project_path": "runs/.../designs/D0001_add_slot_near_feed/project.cst",
  "save_policy": "save_copy",
  "hypothesis": "在馈电附近加入窄槽以增加电流路径并下移谐振。",
  "operations": [
    {
      "type": "add_geometry",
      "target": "metal:slot_feed_1",
      "method": "history_vba_boolean_subtract",
      "parameters": {"slot_l": "8 mm", "slot_w": "0.6 mm"}
    }
  ],
  "expected_effects": ["S11 resonance moves lower", "matching improves near target band"],
  "risks": ["radiation efficiency may drop", "fabrication tolerance becomes tighter"],
  "created_at": "ISO-8601"
}
```

每条 `trials.jsonl` 至少包含：

```json
{
  "trial_id": "T0001",
  "design_id": "D0001",
  "parent_design_id": "D0000",
  "project_path": "runs/.../D0001_add_slot_near_feed/project.cst",
  "parameters": {"slot_l": 8.0, "slot_w": 0.6},
  "metrics": {"s11_min_db": -18.2, "bandwidth_10db_ghz": 0.42, "gain_dbi": 4.8},
  "metric_sources": {"s11": "cst.results tree path ...", "gain": "farfield monitor ..."},
  "status": "completed",
  "logs": ["Result/Model.log"],
  "errors": []
}
```

## 结构演化流程

1. 读取基线：工程路径、参数、结构树、端口、材料、边界、监视器、已有结果。
2. 建立 `D0000_baseline`，保存基线指标和结构摘要。
3. 诊断主问题：匹配、带宽、增益、效率、方向图、极化、尺寸、制造约束。
4. 选择最小有效变异：优先一次只改一个机制，例如馈电、耦合、寄生、开槽、地板、加载、阵列间距。
5. 在副本中应用 History/VBA 修改。
6. Rebuild，并记录几何修改日志。
7. 仿真或读取已有结果。
8. 生成 `metrics.json` 和 `trials.jsonl`。
9. 决定下一轮：继续微调、回退、组合成功变异、转入参数优化或代理模型。

## 常见结构变异类别

- 馈电变异：馈点位置、馈线宽度、馈电间隙、探针位置、耦合馈电间距、匹配枝节。
- 电流路径变异：开槽、折线、蛇形、加载枝节、短路柱、短路片、过孔。
- 耦合变异：寄生单元、耦合缝隙、叠层贴片、超表面单元、加载环。
- 地板变异：地板长度、缺陷地结构、开槽地、倒角、局部接地。
- 辐射体变异：边缘切角、切缝、局部加宽/变窄、多分支、渐变形状。
- 阵列变异：单元间距、馈电相位、幅度加权、去耦结构、阵列边界。
- 材料/层叠变异：介质厚度、介电常数、损耗角、空气层、金属厚度。

## 何时进入优化或代理模型

- 单个结构机制已经有效，但参数组合空间较大。
- 目标是多目标权衡，例如带宽、增益、尺寸和效率同时优化。
- 每次仿真昂贵，需要用代理模型减少 CST 调用。
- 已经积累至少几十到数百条高质量 trial，并且每条都有一致的参数和指标记录。

## 输出要求

每轮报告必须包含：

- `design_id` 和 `parent_design_id`。
- 本轮结构变异摘要。
- CST 工程副本路径。
- 变异假设和预期影响。
- 实际指标和指标来源。
- 是否接受该变异进入下一轮。
- 数据记录文件路径：`design.json`、`metrics.json`、`trials.jsonl`。
