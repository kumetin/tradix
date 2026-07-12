# Lower-Risk Swing Entry Stop-Model Sweep

## Experiment Status

`rejected_for_promotion`

Wider stops improved realized returns and reduced stop-loss rates, but the
setup evaluator still underperformed `SPY` and equal-weight universe exposure
on the train/dev period. This suggests the current stop model was too tight,
but stop width alone is not enough to make the current setup/status rules
promotable.

## Experiment ID

`lower-risk-swing-entry-stop-model-sweep`

## Component Under Test

- Setup evaluator: [`lower-risk-swing-entry`](../../setup-evaluators/lower-risk-swing-entry.md)
- Backtest spec: [`setup-signal-backtest`](../../backtests/components/setup-evaluators/setup-signal-backtest.md)
- Evaluation plan: [`lower-risk-swing-entry-iteration-plan`](../../evaluations/setup-evaluators/lower-risk-swing-entry-iteration-plan.md)
- Baseline: [`lower-risk-swing-entry-baseline-current-stop`](lower-risk-swing-entry-baseline-current-stop.md)

## Evaluation Window

| Setting | Value |
| --- | --- |
| Partition | Train/dev |
| Start date | `2015-01-01` |
| End date | `2019-12-31` |
| Frequency | `weekly` |
| Horizons | `20`, `40`, `60`, `90`, `120` |
| Benchmark | `SPY` |
| Secondary baseline | Equal-weight evaluated universe exposure |
| Universe | [`random-20-non-curated-1`](../../universes/random-20-non-curated-1.md) |
| Evidence score gate | `70` |
| Setup score thresholds | `70`, `80` |

## Stop Models

| Stop model | Meaning |
| --- | --- |
| `current` | Use the evaluator's generated invalidation level. |
| `risk-1.25` | Widen current buy-limit-to-invalidation risk by `1.25x`. |
| `risk-1.5` | Widen current buy-limit-to-invalidation risk by `1.5x`. |
| `support-atr-1.2` | Set stop at support minus `1.2x` ATR. |
| `support-atr-1.5` | Set stop at support minus `1.5x` ATR. |

## Artifact Runs

| Scenario | Artifact directory |
| --- | --- |
| `stop-sweep-20-train-dev-ss70-es70-current` | [`20260711-150433Z__lower-risk-swing-entry__stop-sweep-20-train-dev-ss70-es70-current__a293a606`](../../artifacts/stock/backtests/components/setup-evaluators/setup-signal-backtest/20260711-150433Z__lower-risk-swing-entry__stop-sweep-20-train-dev-ss70-es70-current__a293a606/) |
| `stop-sweep-20-train-dev-ss70-es70-risk-125` | [`20260711-150433Z__lower-risk-swing-entry__stop-sweep-20-train-dev-ss70-es70-risk-125__e7ea19ee`](../../artifacts/stock/backtests/components/setup-evaluators/setup-signal-backtest/20260711-150433Z__lower-risk-swing-entry__stop-sweep-20-train-dev-ss70-es70-risk-125__e7ea19ee/) |
| `stop-sweep-20-train-dev-ss70-es70-risk-15` | [`20260711-150433Z__lower-risk-swing-entry__stop-sweep-20-train-dev-ss70-es70-risk-15__ce8d5088`](../../artifacts/stock/backtests/components/setup-evaluators/setup-signal-backtest/20260711-150433Z__lower-risk-swing-entry__stop-sweep-20-train-dev-ss70-es70-risk-15__ce8d5088/) |
| `stop-sweep-20-train-dev-ss70-es70-support-atr-12` | [`20260711-150433Z__lower-risk-swing-entry__stop-sweep-20-train-dev-ss70-es70-support-atr-12__6da07abc`](../../artifacts/stock/backtests/components/setup-evaluators/setup-signal-backtest/20260711-150433Z__lower-risk-swing-entry__stop-sweep-20-train-dev-ss70-es70-support-atr-12__6da07abc/) |
| `stop-sweep-20-train-dev-ss70-es70-support-atr-15` | [`20260711-150433Z__lower-risk-swing-entry__stop-sweep-20-train-dev-ss70-es70-support-atr-15__cb6f68d0`](../../artifacts/stock/backtests/components/setup-evaluators/setup-signal-backtest/20260711-150433Z__lower-risk-swing-entry__stop-sweep-20-train-dev-ss70-es70-support-atr-15__cb6f68d0/) |
| `stop-sweep-20-train-dev-ss80-es70-current` | [`20260711-150433Z__lower-risk-swing-entry__stop-sweep-20-train-dev-ss80-es70-current__bf69de29`](../../artifacts/stock/backtests/components/setup-evaluators/setup-signal-backtest/20260711-150433Z__lower-risk-swing-entry__stop-sweep-20-train-dev-ss80-es70-current__bf69de29/) |
| `stop-sweep-20-train-dev-ss80-es70-risk-125` | [`20260711-150433Z__lower-risk-swing-entry__stop-sweep-20-train-dev-ss80-es70-risk-125__1da03ad5`](../../artifacts/stock/backtests/components/setup-evaluators/setup-signal-backtest/20260711-150433Z__lower-risk-swing-entry__stop-sweep-20-train-dev-ss80-es70-risk-125__1da03ad5/) |
| `stop-sweep-20-train-dev-ss80-es70-risk-15` | [`20260711-150433Z__lower-risk-swing-entry__stop-sweep-20-train-dev-ss80-es70-risk-15__4452d5d8`](../../artifacts/stock/backtests/components/setup-evaluators/setup-signal-backtest/20260711-150433Z__lower-risk-swing-entry__stop-sweep-20-train-dev-ss80-es70-risk-15__4452d5d8/) |
| `stop-sweep-20-train-dev-ss80-es70-support-atr-12` | [`20260711-150433Z__lower-risk-swing-entry__stop-sweep-20-train-dev-ss80-es70-support-atr-12__03dad801`](../../artifacts/stock/backtests/components/setup-evaluators/setup-signal-backtest/20260711-150433Z__lower-risk-swing-entry__stop-sweep-20-train-dev-ss80-es70-support-atr-12__03dad801/) |
| `stop-sweep-20-train-dev-ss80-es70-support-atr-15` | [`20260711-150433Z__lower-risk-swing-entry__stop-sweep-20-train-dev-ss80-es70-support-atr-15__89c4c084`](../../artifacts/stock/backtests/components/setup-evaluators/setup-signal-backtest/20260711-150433Z__lower-risk-swing-entry__stop-sweep-20-train-dev-ss80-es70-support-atr-15__89c4c084/) |

## Aggregate Results

| Setup threshold | Stop model | Entry mode | Entered | Avg realized | Avg SPY | Avg universe | Edge vs SPY | Edge vs universe | Win rate | Stop rate |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `70` | `current` | `close_entry` | 18815 | 0.78% | 2.90% | 3.81% | -2.12% | -3.03% | 25.50% | 79.12% |
| `70` | `risk-1.25` | `close_entry` | 18815 | 0.94% | 2.90% | 3.81% | -1.96% | -2.87% | 29.96% | 74.55% |
| `70` | `risk-1.5` | `close_entry` | 18815 | 1.11% | 2.90% | 3.81% | -1.79% | -2.69% | 34.39% | 70.18% |
| `70` | `support-atr-1.2` | `close_entry` | 18815 | 1.08% | 2.90% | 3.81% | -1.82% | -2.72% | 33.44% | 71.27% |
| `70` | `support-atr-1.5` | `close_entry` | 18815 | 1.26% | 2.90% | 3.81% | -1.64% | -2.54% | 38.60% | 65.72% |
| `80` | `current` | `close_entry` | 10900 | 0.48% | 2.59% | 3.81% | -2.11% | -3.32% | 24.76% | 80.80% |
| `80` | `risk-1.25` | `close_entry` | 10900 | 0.64% | 2.59% | 3.81% | -1.95% | -3.17% | 29.34% | 76.14% |
| `80` | `risk-1.5` | `close_entry` | 10900 | 0.75% | 2.59% | 3.81% | -1.84% | -3.06% | 33.55% | 72.19% |
| `80` | `support-atr-1.2` | `close_entry` | 10900 | 0.71% | 2.59% | 3.81% | -1.87% | -3.09% | 32.74% | 73.12% |
| `80` | `support-atr-1.5` | `close_entry` | 10900 | 0.84% | 2.59% | 3.81% | -1.75% | -2.97% | 37.84% | 67.77% |

Limit-entry rows followed the same ordering but were worse than close-entry for
every tested stop model.

## Findings

- Wider stops improved average realized return, win rate, and stop-loss rate in
  a consistent direction.
- `support-atr-1.5` was the best stop model in this sweep.
- `setup_score >= 70` continued to outperform `setup_score >= 80`; stricter
  setup-score filtering did not improve results.
- Even the best stop variant still underperformed both `SPY` and equal-weight
  universe exposure across the aggregate train/dev result.
- Longer horizons improved raw realized return but also increased benchmark and
  universe opportunity cost.
- Stop rates remain high even after widening, which points to a deeper issue in
  setup-status permissiveness, take-profit/reward construction, or both.

## Decision

Do not promote stop-only changes to validation.

Use `support-atr-1.5` as the provisional stop model for the next train/dev
iteration because it is clearly better than the current stop model, but treat
it as only one part of the fix.

## Next Experiment

Keep the same train/dev period and 20-stock non-curated universe.

Recommended next grid:

| Dimension | Values |
| --- | --- |
| Setup score threshold | `70` |
| Evidence score gate | `70`, fixed |
| Stop model | `support-atr-1.5` |
| Horizons | `20`, `40`, `60`, `90`, `120` |
| Setup status rule | Current versus stricter `Ready / near buy zone` rule |
| Take-profit model | Current versus nearer partial target |

The next question is whether the evaluator is admitting too many low-quality
`Ready / near buy zone` setups, or whether the take-profit model is too far from
realistic swing outcomes.
