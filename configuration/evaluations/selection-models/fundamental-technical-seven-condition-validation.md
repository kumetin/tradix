# Fundamental Technical Seven-Condition
[Evaluation](../../../stages/OPERATIONS.md#evaluation-plans)

## Settings

| Setting | Value |
| --- | --- |
| `warmup_start` | `2024-01-02` |
| `evaluation_start` | `2025-02-03` |
| `evaluation_end` | `2025-07-18` |
| `split_method` | Single previously unused validation window; no locked holdout |
| `cadence` | Weekly, last completed SPY session per ISO week |
| `horizons` | `21`, `63`, `126`, `252` valid sessions |

Warm-up rows initialize rolling features and are excluded from metrics. This
window was not used in the exploratory condition-count or matched-ablation
experiments. Inspecting it makes it validation evidence for the frozen
seven-condition model, not a reusable clean holdout for subsequent rule
changes.
