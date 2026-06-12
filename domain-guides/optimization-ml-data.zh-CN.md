# CST 优化、数据记录和代理模型版本管理指南

## 目标

本指南用于把 CST 仿真、结构演化、参数优化和机器学习/深度学习代理模型连接成可追溯闭环。重点是记录每个设计版本、仿真 trial、数据集版本、训练配置、模型权重和 CST 验证结果。

## 总体闭环

1. 设定目标、约束、变量、预算和停止条件。
2. 建立基线设计 `D0000` 和基线指标。
3. 每个候选生成唯一 `design_id` 和 `trial_id`。
4. 在工程副本中应用参数或结构变异。
5. Rebuild、仿真、读取指标、记录日志。
6. 追加 `trials.jsonl`。
7. 定期从 `trials.jsonl` 生成版本化数据集。
8. 训练或更新代理模型。
9. 用代理模型提出候选，再回到 CST 验证。
10. 用 CST 验证结果更新数据集和模型版本。

## 推荐目录

```text
runs/
  antenna-task-YYYYMMDD-HHMMSS/
    manifest.json
    trials.jsonl
    datasets/
      dataset_v001/
        dataset.parquet
        dataset_summary.json
        split.json
      dataset_v002/
    models/
      surrogate_v001/
        model_card.json
        train_config.json
        metrics.json
        weights.pt
      surrogate_v002/
    designs/
      D0000_baseline/
      D0001_...
```

## manifest.json

```json
{
  "task_id": "antenna-task-20260602-153000",
  "objective": "maximize bandwidth with S11 < -10 dB while keeping gain > 5 dBi",
  "base_project_path": "D:/path/base.cst",
  "save_policy": "save_copy",
  "variables": {
    "slot_l": {"min": 2.0, "max": 12.0, "unit": "mm"},
    "feed_x": {"min": -4.0, "max": 4.0, "unit": "mm"}
  },
  "constraints": ["gain_dbi >= 5", "efficiency_total >= 0.65"],
  "budget": {"max_trials": 80, "max_hours": 24},
  "current_dataset_version": "dataset_v001",
  "current_surrogate_version": "surrogate_v001"
}
```

## trials.jsonl 字段

每个 trial 必须是一行 JSON：

```json
{
  "trial_id": "T0017",
  "design_id": "D0017",
  "parent_design_id": "D0012",
  "mutation_id": "M0017",
  "project_path": "runs/.../designs/D0017/project.cst",
  "parameters": {"slot_l": 7.2, "feed_x": 1.1},
  "structure_ops": ["add_slot", "adjust_feed"],
  "metrics": {
    "s11_min_db": -21.4,
    "bandwidth_10db_ghz": 0.58,
    "gain_dbi": 5.3,
    "efficiency_total": 0.72
  },
  "metric_sources": {
    "s11": "cst.results:1D Results/S-Parameters/S1,1",
    "gain": "farfield:f=3.5GHz"
  },
  "simulation": {
    "solver": "frequency_domain",
    "started_at": "ISO-8601",
    "ended_at": "ISO-8601",
    "duration_s": 1830,
    "status": "completed"
  },
  "versions": {
    "dataset_version": "dataset_v001",
    "surrogate_version_used": "surrogate_v001",
    "surrogate_prediction_id": "P0034"
  },
  "logs": ["Result/Model.log"],
  "errors": []
}
```

## 数据集版本管理

生成新数据集版本时记录：

- 来源 trial 范围和过滤规则。
- 参数列、结构编码列、指标列和单位。
- 删除了哪些失败样本，保留了哪些负样本。
- train/validation/test 划分方法和随机种子。
- 数据 hash 或文件大小。
- 与上一版本相比新增样本数量。

`dataset_summary.json` 示例：

```json
{
  "dataset_version": "dataset_v002",
  "source_trials": "T0001-T0080",
  "num_samples": 76,
  "num_failed_excluded": 4,
  "features": ["slot_l_mm", "feed_x_mm", "mutation_type"],
  "targets": ["bandwidth_10db_ghz", "gain_dbi", "efficiency_total"],
  "split_seed": 20260602,
  "created_from_commit": "git-sha-if-available"
}
```

## 代理模型版本管理

每个 `surrogate_v*` 必须有 `model_card.json`：

```json
{
  "surrogate_version": "surrogate_v002",
  "dataset_version": "dataset_v002",
  "model_type": "xgboost | random_forest | gaussian_process | neural_network | graph_model",
  "input_features": ["slot_l_mm", "feed_x_mm", "mutation_type"],
  "output_targets": ["bandwidth_10db_ghz", "gain_dbi"],
  "train_config_path": "train_config.json",
  "weights_path": "weights.pt",
  "validation_metrics": {"mae_bandwidth": 0.04, "mae_gain": 0.28},
  "known_limits": ["valid only for D0000-derived slot/feed mutations"],
  "created_at": "ISO-8601"
}
```

不能只保存权重文件。必须保存训练配置、数据版本、指标和适用范围。

## 选择优化方法

- 少量连续变量、仿真昂贵：贝叶斯优化或高斯过程。
- 离散结构变异多：遗传算法、进化策略、树搜索或规则驱动候选生成。
- 已有大量数据：随机森林、XGBoost、神经网络、图模型或几何编码模型。
- 多目标：记录 Pareto 前沿，不要强行只优化一个指标。
- 强约束：先过滤不可制造、端口错误、效率过低或尺寸超限的候选。

## 主动学习规则

代理模型提出候选时，选择：

- 预测性能最好的 top-k。
- 不确定性高但可能有价值的样本。
- 覆盖参数空间边界的样本。
- 验证代理模型可能过度自信的样本。

每个候选必须写 `surrogate_prediction_id`，CST 验证后写入实际指标，便于评估代理误差。

## 停止条件

- 达到预算。
- Pareto 前沿多轮无明显提升。
- 代理模型误差低但 CST 验证无法继续提升。
- 所有建议变异都违反制造、尺寸、效率或端口约束。
- 用户要求停止。

## 输出要求

优化或 ML 任务完成后报告：

- 当前最佳 `design_id` 和工程路径。
- 最佳指标和来源。
- 已运行 trial 数量、失败数量、有效样本数量。
- 当前 `dataset_version` 和 `surrogate_version`。
- 数据集、模型卡、训练配置、权重、日志路径。
- Pareto 或 top-k 候选摘要。
- 下一步建议和风险。
