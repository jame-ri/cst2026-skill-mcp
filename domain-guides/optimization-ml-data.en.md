# CST Optimization, Data Logging, And Surrogate Versioning Guide

## Purpose

Use this guide to connect CST simulations, structural evolution, parameter optimization, and machine-learning or deep-learning surrogate models into a traceable loop. Record every design version, simulation trial, dataset version, training config, model weights, and CST validation result.

## Overall Loop

1. Define objectives, constraints, variables, budget, and stopping rules.
2. Create baseline design `D0000` and baseline metrics.
3. Assign each candidate a unique `design_id` and `trial_id`.
4. Apply parameter or structural mutations in a project copy.
5. Rebuild, simulate, read metrics, and record logs.
6. Append `trials.jsonl`.
7. Periodically generate versioned datasets from `trials.jsonl`.
8. Train or update a surrogate model.
9. Use the surrogate to propose candidates, then validate in CST.
10. Use CST validation results to update the dataset and model versions.

## Recommended Layout

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

## trials.jsonl Fields

Each trial must be one JSON line:

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

## Dataset Versioning

When creating a new dataset version, record:

- Source trial range and filtering rules.
- Parameter columns, structure-encoding columns, metric columns, and units.
- Which failed samples were removed and which negative samples were kept.
- Train/validation/test split method and random seed.
- Data hash or file size.
- Number of new samples compared with the previous version.

`dataset_summary.json` example:

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

## Surrogate Model Versioning

Every `surrogate_v*` must have a `model_card.json`:

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

Do not save only weights. Always save training config, dataset version, metrics, and applicability limits.

## Choosing An Optimizer

- Few continuous variables and expensive simulations: Bayesian optimization or Gaussian processes.
- Many discrete structural mutations: genetic algorithms, evolution strategies, tree search, or rule-driven candidate generation.
- Large datasets: random forests, XGBoost, neural networks, graph models, or geometry-encoding models.
- Multi-objective tasks: record the Pareto front; do not force everything into one scalar metric.
- Strong constraints: filter candidates that violate fabrication, port validity, efficiency, size, or other limits.

## Active Learning Rules

When the surrogate proposes candidates, select:

- Top-k candidates by predicted performance.
- High-uncertainty samples with possible value.
- Samples near parameter-space boundaries.
- Samples that test likely surrogate overconfidence.

Every candidate must have a `surrogate_prediction_id`; after CST validation, store actual metrics to evaluate surrogate error.

## Stopping Rules

- Budget reached.
- Pareto front does not improve across multiple rounds.
- Surrogate error is low, but CST validation no longer improves.
- Suggested mutations violate fabrication, size, efficiency, or port constraints.
- User asks to stop.

## Output Requirements

After optimization or ML work, report:

- Current best `design_id` and project path.
- Best metrics and sources.
- Number of trials, failures, and valid samples.
- Current `dataset_version` and `surrogate_version`.
- Dataset, model card, training config, weights, and log paths.
- Pareto or top-k candidate summary.
- Next recommendation and risks.
