# Evaluations

This directory describes how configured backtests are evaluated across
historical data windows.

[Evaluation plans](../../stages/OPERATIONS.md#evaluation-plans) are experiment
configuration, not executable strategy stages or independently benchmarkable
components.

Evaluation definitions own:

- available data windows
- warm-up windows used to initialize indicators
- train/validation/test split methods
- walk-forward or rolling-window schedules
- final out-of-sample periods

Strategy theses and rules live under `strategies/`. Configured strategy
backtest specifications live under `backtests/`. Generated evaluation artifacts
should live under `artifacts/stock/backtests/`.

## Available Evaluations

- [Classic 12-1 Momentum Rotation TC-001 Post-Validation Confirmation](classic-12-1-momentum-rotation/tc-001-post-validation-confirmation.md)
- [Momentum Rotation TC-001 Full Period](momentum-rotation/tc-001-full-period.md)
- [Momentum Rotation TC-002 Full Period](momentum-rotation/tc-002-full-period.md)
- [Momentum Rotation TC-003 Full Period](momentum-rotation/tc-003-full-period.md)
- [Lower-Risk Swing Entry Iteration Plan](setup-evaluators/lower-risk-swing-entry-iteration-plan.md)
- [Technical Resistance Runner TC-001 Development and Retrospective Period](technical-resistance-runner/tc-001-development-retrospective.md)
- [Technical Resistance Runner TC-003 Pre-2014 Regimes](technical-resistance-runner/tc-003-pre-2014-regimes.md)
- [Regime-Gated Technical Resistance TC-001 Eight-Dataset Robustness](regime-gated-technical-resistance/tc-001-eight-dataset-robustness.md)

## Date Semantics

Use explicit date names:

| Field | Meaning |
| --- | --- |
| `warmup_start` | First date loaded only to initialize indicators and rolling features. |
| `evaluation_start` | First date included in reported performance metrics. |
| `evaluation_end` | Last date included in reported performance metrics. |

Do not include warm-up-only rows in CAGR, drawdown, trade-return, or benchmark
metrics.
