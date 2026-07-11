# Setup Signal Backtest

## Component Under Test

Component type: [`setup-evaluator`](../../../setup-evaluators/README.md)

[Setup Evaluators](../../../setup-evaluators/README.md)

## Question

If a [setup evaluator](../../../setup-evaluators/README.md) emits repeatable point-in-time setup signals, does
following those signals above defined action, score, and confidence thresholds
produce durable realized returns over time compared with simple baselines such
as `SPY`, equal-weight universe exposure, and unfiltered signal exposure?

This is a component-level backtest. It tests the [setup evaluator](../../../setup-evaluators/README.md)'s signal
playbook, not a full portfolio strategy with cash allocation, overlapping
positions, settlement, fees, slippage, taxes, or rebalance constraints.

## Backtest Type

`isolated component backtest`

## Direct Input/Output Contract

This backtest evaluates [setup-evaluator](../../../setup-evaluators/README.md)
signals directly against forward price outcomes. It does not require a
[strategy flow](../../../strategies/README.md),
[portfolio policy](../../../portfolio-policies/README.md),
[funding profile](../../../funding-profiles/README.md), or
[execution model](../../../execution-models/README.md).

| Contract | Definition |
| --- | --- |
| Input universe | Explicit ticker list supplied to the benchmark runner. See [universes](../../../universes/README.md) for reusable universe profiles. |
| Input data | Point-in-time rows from local daily feature files. |
| Component output | Normalized `SetupSignal` records. |
| Outcome model | Entry-mode simulation with first-exit realized P&L. |
| Baselines | `SPY`, equal-weight evaluated ticker set, unfiltered `buy` signals, and future random baselines. |

## Setup Signal Interface

Each setup evaluator adapter must emit normalized `SetupSignal` records:

| Field | Meaning |
| --- | --- |
| `evaluator_id` | Stable evaluator identifier. |
| `ticker` | Evaluated symbol. |
| `evaluation_date` | Point-in-time decision date. |
| `action` | Normalized signal action such as `buy`, `wait`, or `avoid`. |
| `score` | Numeric signal strength, where higher is better. |
| `confidence` | Numeric data/setup confidence, where higher is better. |
| `current_price` | Decision-date adjusted price. |
| `entry_price` | Price used for immediate-entry tests. |
| `buy_limit` | Limit-entry trigger price, if applicable. |
| `stop_loss` | Initial downside exit level. |
| `take_profit` | Upside exit level. |
| `metadata` | Evaluator-specific fields such as score breakdowns or setup labels. |

The generic backtest engine should know only this interface. Evaluator-specific
labels, scoring component names, and setup explanations belong in `metadata`.

## Variants

| Variant | Entry assumption | Horizons |
| --- | --- | --- |
| Close-entry signal test | Enter `buy` signals at evaluation-date adjusted close. | `5`, `10`, `20`, `40`, `60` trading days |
| Limit-entry trade-plan test | Enter `buy` signals only after the generated buy limit is touched. | `5`, `10`, `20`, `40`, `60` trading days |

Threshold sweeps should test multiple `min_score` and `min_confidence` values
instead of assuming the evaluator's default action alone is selective enough.

## Entry Mode

`entry_mode` separates two research questions:

| Entry mode | Meaning | Use |
| --- | --- | --- |
| `close_entry` | Enter at the evaluation-date adjusted close. | Tests whether the signal predicts forward strength from the decision date. |
| `limit_entry` | Enter only if a later daily adjusted low touches the generated buy limit within the horizon. | Tests whether the generated trade plan offers a pullback entry and then performs after entry. |

The horizon is a measurement window, not a monitoring interval. A `20` trading
day horizon means the benchmark looks at every daily row during the next `20`
trading days.

`realized_return` uses first-exit trade P&L. If take profit or stop loss is
touched inside the horizon, the trade exits at that level. If neither is
touched, it exits at the horizon-end adjusted close.

`horizon_return` separately records the raw entry-to-horizon-end return for
signal research. Do not use `horizon_return` as trade P&L when an exit event
occurred before the horizon ended.

## Evaluation Matrix

- [TC-001 Full Period](../../../evaluations/momentum-rotation/tc-001-full-period.md)
- Add separate market-regime and locked-holdout windows before treating an
  evaluator as reusable inside automated strategies.

## Metrics

| Metric | Reason |
| --- | --- |
| Realized return by action, score, and confidence bucket | Measures whether signal strength predicts first-exit trade P&L. |
| Win rate | Checks directional usefulness. |
| Max favorable excursion | Measures upside opportunity after the signal. |
| Max adverse excursion | Measures realized downside pressure after the signal. |
| Take-profit rate | Tests whether projected upside exits are reachable. |
| Stop-loss rate | Tests whether downside exits are too tight or too frequently hit. |
| Limit-entry trigger rate | Separates good signals from plans that never offer the intended entry. |
| Benchmark-relative return | Compares the signal against `SPY` and equal-weight evaluated universe exposure. |

## Baselines

- `SPY` forward return over the same dates and horizons.
- Equal-weight forward return of the evaluated ticker set.
- Unfiltered `buy` signal average.
- Random ticker or random signal baseline once repeated sampling is added.
- DCA `SPY` when this benchmark is composed into a portfolio-level strategy.

## Interpretation Rules

Treat a [setup evaluator](../../../setup-evaluators/README.md) as promising only if qualifying `buy` signals show
better realized return, win rate, adverse excursion, or benchmark-relative
return across more than one horizon and evaluation period.

Treat weak monotonicity, low limit-entry trigger rates, high stop-loss rates, or
results driven by one ticker or one market regime as evidence that the evaluator
needs revised signal rules before automated use.

## Output Location

Generated artifacts should live under:

```text
artifacts/stock/backtests/components/setup-evaluators/setup-signal-backtest/<evaluator-id>/
```

Each run should write:

| Artifact | Purpose |
| --- | --- |
| `run_config.csv` | Records evaluator, tickers, dates, horizons, benchmark, entry actions, and score/confidence thresholds. |
| `predictions.csv` | Point-in-time normalized setup signals plus evaluator-specific metadata. |
| `outcomes.csv` | Entry-mode outcomes with first-exit realized P&L. |
| `summary.csv` | Grouped metrics by action, rank, score, confidence, and evaluator-specific summary fields. |
