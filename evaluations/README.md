# Evaluations

This directory describes how configured backtests are evaluated across
historical data windows.

Evaluation definitions own:

- available data windows
- warm-up windows used to initialize indicators
- train/validation/test split methods
- walk-forward or rolling-window schedules
- final out-of-sample periods

Strategy rules live under `strategies/`. Configured strategy instances live
under `backtests/`. Generated evaluation artifacts should live under
`artifacts/stock/backtests/`.

## Available Evaluations

- [Momentum Rotation TC-001 Full Period](momentum-rotation/tc-001-full-period.md)
- [Momentum Rotation TC-002 Full Period](momentum-rotation/tc-002-full-period.md)
- [Momentum Rotation TC-003 Full Period](momentum-rotation/tc-003-full-period.md)
- [Lower-Risk Swing Entry Iteration Plan](setup-evaluators/lower-risk-swing-entry-iteration-plan.md)

## Date Semantics

Use explicit date names:

| Field | Meaning |
| --- | --- |
| `warmup_start` | First date loaded only to initialize indicators and rolling features. |
| `evaluation_start` | First date included in reported performance metrics. |
| `evaluation_end` | Last date included in reported performance metrics. |

Do not include warm-up-only rows in CAGR, drawdown, trade-return, or benchmark
metrics.
