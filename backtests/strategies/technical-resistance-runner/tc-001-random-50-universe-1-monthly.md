# TC-001: Random 50 Universe 1 Monthly Single Position

Strategy: [Technical Resistance Runner](../../../strategies/technical-resistance-runner.md)

## Configuration Intent

### Strategy Behavior Implemented

Within random static 50-stock universe 1, the highest technical resistance
score at each available monthly decision is expected to have a higher
six-month target-hit rate and risk-adjusted return than weaker-scored members.
Selling 75% after a 5.21% surge and the remaining 25% at setup resistance is
expected to capture typical favorable excursions while preserving some
continuation exposure through the 126-session horizon.

### Configuration Controls

The primary variant fixes one active position, no price stop, a sequential 75%
sale at +5.21%, a 25% setup-resistance sale, and a 126-session maximum hold.
Monthly signals that occur while a position is active are recorded but not
entered. The universe, signal cutoff, next-session entry, capital, execution
assumptions, and evaluation partitions remain controlled.

### Evaluation Sensitivities

The claim is weakened if score buckets are not monotonic, the top selection
does not beat SPY or equal-weight dated membership after costs, target
reachability is not better than simple baselines, the sequential two-stage
policy does not beat both full-target and full-horizon variants, or results rely on a few
extreme winners or current-constituent leakage.

## [Static Universe](../../../stages/OPERATIONS.md#universe-resolution-and-universe-models)

[Random S&P 500 Stocks 50 — Universe 1](../../../configuration/universes/random-sp500-50-1.md)

This fixed current-constituent sample intentionally makes TC-001 a
current-universe-biased research test. Membership remains controlled across all
dates and variants; results must not be described as point-in-time S&P 500
performance.

## [Selection Model](../../../stages/OPERATIONS.md#selection-and-selection-models)

[Technical Resistance Score](../../../stages/selection-models/technical-resistance-score.md)

| Parameter | Value |
| --- | --- |
| `target_count` | `1` |
| `support_low_window` | `63` trading sessions |
| `resistance_window` | `126` trading sessions |
| `relative_return_windows` | `63, 126, 252` trading sessions |
| `relative_percentile_window` | `126` trading sessions |
| `rsi_window` | `14` trading sessions |
| `volume_window` | `20` trading sessions |
| `missing_data_policy` | `exclude_and_report` |
| `tie_breaker` | ascending stable instrument ID |

## Strategy Parameters

| Parameter | Value |
| --- | --- |
| `target_lookback_days` | `126` trading sessions |
| `first_profit_return` | `0.0521` |
| `first_profit_sale_fraction` | `0.75` |
| `second_profit_sale_fraction` | `0.25` |
| `maximum_holding_days` | `126` trading sessions |

## [Trigger](../../../stages/OPERATIONS.md#trigger)

[Monthly Allocation](../../../configuration/triggers/monthly-allocation.md)

Use the last complete session before the month begins as the decision cutoff.
Enter only when the portfolio is flat.

## Entry Rule

After an eligible top selection is known, submit the entry after the decision
close for execution at the next trading session's adjusted open. Never fill at
the close that produced the score.

## [Funding](../../../stages/OPERATIONS.md#funding-profiles)

[Initial 5000 Only](../../../configuration/funding/initial-5000-only.md)

No capital is contributed after the initial allocation.

## [Portfolio Policy](../../../stages/OPERATIONS.md#portfolio-transitions-and-portfolio-policies)

[Single Position Two Stage Profit Horizon Exit](../../../stages/portfolio-policies/single-position-two-stage-profit-horizon-exit.md)

The policy ignores and reports new monthly targets while a position is active.
It sells 75% at +5.21%, then the remaining 25% at setup resistance, applies no
stop, and liquidates all unsold shares on session 126 after entry.

## [Execution](../../../stages/OPERATIONS.md#execution-and-execution-models) and Accounting

[Daily-Bar Frictionless Fractional](../../../stages/execution-models/daily-bar-frictionless-fractional.md)

This primary research run uses fractional shares and zero fees, taxes, slippage,
and settlement lag. A later robustness run must apply realistic costs and
settlement without changing the primary specification.

## [Evaluation](../../../stages/OPERATIONS.md#evaluation-plans)

[TC-001 Development and Retrospective Period](../../../configuration/evaluations/technical-resistance-runner/tc-001-development-retrospective.md)

## Benchmarks

- `SPY` buy and hold over identical reported partitions
- Equal-weight random universe 1
- Random eligible single-stock selection with identical entry and exit handling
- Highest 126-session-return candidate with identical entry and exit handling
- Full position sold at resistance
- Full position held for 126 trading sessions

## Metrics

- total and annualized time-weighted return;
- trade-level arithmetic and geometric mean return;
- median return, win rate, and profit factor;
- maximum drawdown and worst trade;
- target-hit rate and first-hit trading-session distribution;
- maximum favorable and adverse excursion before exit;
- score-decile target-hit rate and forward-return monotonicity;
- SPY-relative and equal-weight-universe-relative return;
- active-position signal skip rate, exposure, turnover, and cash drag; and
- results by development, walk-forward validation, contaminated retrospective period, market
  regime, sector, and selected ticker concentration.

## Supported Overrides

Run these as separate labeled comparisons. The former holdout has already
influenced the exit rule and is therefore retrospective evidence only:

1. Primary: sell 75% at +5.21%, then 25% at resistance.
2. Prior rule: sell 50% at resistance and residual at 126 sessions.
3. Full-target: sell 100% at resistance; otherwise exit at 126 sessions.
4. Full-horizon: ignore resistance and sell 100% at 126 sessions.

## Output Location

Generated configuration, predictions, orders, fills, positions, trades,
partition metrics, benchmark series, and execution report belong under:

```text
artifacts/stock/backtests/strategies/technical-resistance-runner/tc-001/
```
