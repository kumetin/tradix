# Lower-Risk Swing Entry Baseline: Current Stop

## Experiment Status

`rejected_for_promotion`

This experiment is retained as the baseline for the current lower-risk
swing-entry evaluator and current stop/invalidation model. It should not be
promoted to validation, but it should be kept as negative evidence so future
iterations can be compared against it.

## Experiment ID

`lower-risk-swing-entry-baseline-current-stop`

## Component Under Test

- Setup evaluator: [`lower-risk-swing-entry`](../../setup-evaluators/lower-risk-swing-entry.md)
- Backtest spec: [`setup-signal-backtest`](../../backtests/components/setup-evaluators/setup-signal-backtest.md)
- Evaluation plan: [`lower-risk-swing-entry-iteration-plan`](../../evaluations/setup-evaluators/lower-risk-swing-entry-iteration-plan.md)

## Evaluation Window

| Setting | Value |
| --- | --- |
| Partition | Train/dev |
| Start date | `2015-01-01` |
| End date | `2019-12-31` |
| Warm-up source | Local feature rows from `2014-01-01` onward where available |
| Frequency | `weekly` |
| Benchmark | `SPY` |
| Secondary baseline | Equal-weight evaluated universe exposure |

## Universe

Smoke used the first five names from
[`random-20-non-curated-1`](../../universes/random-20-non-curated-1.md).

Fast sweep used all 20 names from
[`random-20-non-curated-1`](../../universes/random-20-non-curated-1.md).

## Artifact Runs

| Run group | Scenario | Artifact directory |
| --- | --- | --- |
| Smoke | `smoke-5-train-dev-core` | [`20260711-143625Z__lower-risk-swing-entry__smoke-5-train-dev-core__4b7e5bc4`](../../artifacts/stock/backtests/components/setup-evaluators/setup-signal-backtest/20260711-143625Z__lower-risk-swing-entry__smoke-5-train-dev-core__4b7e5bc4/) |
| Fast sweep | `fast-20-train-dev-ss70-es50` | [`20260711-143723Z__lower-risk-swing-entry__fast-20-train-dev-ss70-es50__13b47435`](../../artifacts/stock/backtests/components/setup-evaluators/setup-signal-backtest/20260711-143723Z__lower-risk-swing-entry__fast-20-train-dev-ss70-es50__13b47435/) |
| Fast sweep | `fast-20-train-dev-ss70-es70` | [`20260711-143723Z__lower-risk-swing-entry__fast-20-train-dev-ss70-es70__90f9da90`](../../artifacts/stock/backtests/components/setup-evaluators/setup-signal-backtest/20260711-143723Z__lower-risk-swing-entry__fast-20-train-dev-ss70-es70__90f9da90/) |
| Fast sweep | `fast-20-train-dev-ss70-es85` | [`20260711-143723Z__lower-risk-swing-entry__fast-20-train-dev-ss70-es85__5ff4b23b`](../../artifacts/stock/backtests/components/setup-evaluators/setup-signal-backtest/20260711-143723Z__lower-risk-swing-entry__fast-20-train-dev-ss70-es85__5ff4b23b/) |
| Fast sweep | `fast-20-train-dev-ss80-es50` | [`20260711-143723Z__lower-risk-swing-entry__fast-20-train-dev-ss80-es50__0fef34b4`](../../artifacts/stock/backtests/components/setup-evaluators/setup-signal-backtest/20260711-143723Z__lower-risk-swing-entry__fast-20-train-dev-ss80-es50__0fef34b4/) |
| Fast sweep | `fast-20-train-dev-ss80-es70` | [`20260711-143723Z__lower-risk-swing-entry__fast-20-train-dev-ss80-es70__2d0170e4`](../../artifacts/stock/backtests/components/setup-evaluators/setup-signal-backtest/20260711-143723Z__lower-risk-swing-entry__fast-20-train-dev-ss80-es70__2d0170e4/) |
| Fast sweep | `fast-20-train-dev-ss80-es85` | [`20260711-143723Z__lower-risk-swing-entry__fast-20-train-dev-ss80-es85__968e5aa0`](../../artifacts/stock/backtests/components/setup-evaluators/setup-signal-backtest/20260711-143723Z__lower-risk-swing-entry__fast-20-train-dev-ss80-es85__968e5aa0/) |
| Fast sweep | `fast-20-train-dev-ss90-es50` | [`20260711-143723Z__lower-risk-swing-entry__fast-20-train-dev-ss90-es50__467c3eb5`](../../artifacts/stock/backtests/components/setup-evaluators/setup-signal-backtest/20260711-143723Z__lower-risk-swing-entry__fast-20-train-dev-ss90-es50__467c3eb5/) |
| Fast sweep | `fast-20-train-dev-ss90-es70` | [`20260711-143723Z__lower-risk-swing-entry__fast-20-train-dev-ss90-es70__49067b56`](../../artifacts/stock/backtests/components/setup-evaluators/setup-signal-backtest/20260711-143723Z__lower-risk-swing-entry__fast-20-train-dev-ss90-es70__49067b56/) |
| Fast sweep | `fast-20-train-dev-ss90-es85` | [`20260711-143723Z__lower-risk-swing-entry__fast-20-train-dev-ss90-es85__257c0887`](../../artifacts/stock/backtests/components/setup-evaluators/setup-signal-backtest/20260711-143723Z__lower-risk-swing-entry__fast-20-train-dev-ss90-es85__257c0887/) |

Each artifact directory contains `run_config.csv`, `predictions.csv`,
`predictions.html`, `outcomes.csv`, `summary.csv`, and `execution-report.md`.

## Fast-Sweep Summary

| Config | Entry mode | Entered total | Avg realized | Avg SPY | Avg equal-weight universe | Edge vs SPY | Edge vs universe | Avg stop rate |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| SS 70 / ES 50 | `close_entry` | 15052 | 0.66% | 1.59% | 2.07% | -0.93% | -1.42% | 71.72% |
| SS 70 / ES 70 | `close_entry` | 15052 | 0.66% | 1.59% | 2.07% | -0.93% | -1.42% | 71.72% |
| SS 80 / ES 50 | `close_entry` | 8720 | 0.42% | 1.36% | 2.07% | -0.93% | -1.65% | 73.51% |
| SS 80 / ES 70 | `close_entry` | 8720 | 0.42% | 1.36% | 2.07% | -0.93% | -1.65% | 73.51% |
| SS 90 / ES 50 | `close_entry` | 940 | 0.18% | 1.24% | 2.07% | -1.06% | -1.89% | 76.17% |
| SS 90 / ES 70 | `close_entry` | 940 | 0.18% | 1.24% | 2.07% | -1.06% | -1.89% | 76.17% |
| SS 70 / ES 50 | `limit_entry` | 14364 | 0.29% | 1.48% | 2.07% | -1.19% | -1.78% | 75.06% |
| SS 70 / ES 70 | `limit_entry` | 14364 | 0.29% | 1.48% | 2.07% | -1.19% | -1.78% | 75.06% |
| SS 80 / ES 50 | `limit_entry` | 8349 | 0.09% | 1.27% | 2.07% | -1.19% | -1.99% | 76.68% |
| SS 80 / ES 70 | `limit_entry` | 8349 | 0.09% | 1.27% | 2.07% | -1.19% | -1.99% | 76.68% |
| SS 90 / ES 50 | `limit_entry` | 881 | -0.22% | 1.09% | 2.07% | -1.32% | -2.30% | 81.19% |
| SS 90 / ES 70 | `limit_entry` | 881 | -0.22% | 1.09% | 2.07% | -1.32% | -2.30% | 81.19% |
| Any SS / ES 85 | `close_entry` or `limit_entry` | 0 | N/A | N/A | N/A | N/A | N/A | N/A |

## Findings

- The current evaluator and current stop model should not be promoted beyond
  train/dev.
- Higher `setup_score` did not improve train/dev outcomes. `SS 90` produced
  fewer trades and worse average realized return than `SS 70`.
- `evidence_score` is not currently a useful sweep dimension. Most predictions
  have `evidence_score=80`; thresholds `50` and `70` behave identically, while
  `85` removes every eligible trade.
- The current stop/invalidation model appears too tight or the setup-status
  rules are too permissive. Stop rates ranged from roughly 72% to 81% across
  the main sweep.
- `limit_entry` underperformed `close_entry`, so the generated buy-limit plus
  stop/take-profit trade plan is not adding value yet.
- All tested configurations underperformed both `SPY` and equal-weight universe
  exposure during train/dev.

## Decision

Do not continue sweeping `evidence_score` or stricter `setup_score` thresholds
for the current evaluator.

Use this experiment as the baseline for the next train/dev iteration.

## Next Experiment

Keep the same train/dev period and 20-stock non-curated universe, but introduce
explicit stop-model variants before moving to validation.

Recommended next grid:

| Dimension | Values |
| --- | --- |
| Setup score threshold | `70`, `80` |
| Evidence score gate | `50` or `70`, fixed |
| Horizons | `20`, `40`, `60`, `90`, `120` |
| Stop model | `current`, `1.25x current risk`, `1.5x current risk`, `support - 1.2x ATR`, `support - 1.5x ATR` |
| Entry action | `buy` |

The next question is whether the evaluator has signal that is being cut off by
tight stops, or whether the setup-score/status rules themselves are not
predictive.
