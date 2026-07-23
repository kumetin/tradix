# Continuous Fundamental Momentum Validation

[Evaluation](../../../stages/OPERATIONS.md#evaluation-plans)

## Settings

| Setting | Value |
| --- | --- |
| `warmup_start` | `2024-07-01` |
| `evaluation_start` | `2025-07-21` |
| `evaluation_end` | `2026-01-16` |
| `split_method` | Single previously unused validation window; no locked holdout |
| `cadence` | Weekly, last completed SPY session per ISO week |
| `horizons` | `21`, `63`, `126` valid sessions |

Warm-up rows initialize rolling features and are excluded from metrics. This
window begins after the inspected seven-condition validation period. Inspecting
it makes it validation evidence for this frozen model, not a reusable clean
holdout for subsequent rule or weight changes. A 252-session horizon is omitted
because the persisted tape does not provide that outcome for the full window.
