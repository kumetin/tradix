# TC-002: Random 50 Universe 1 Daily SMA50 Exit

Strategy: [Technical Resistance Runner](../../../strategies/technical-resistance-runner.md)

## Configuration Intent

Whether daily SMA50 invalidation reduces the no-stop strategy's tail losses
without sacrificing enough favorable setups to destroy total and
benchmark-relative return.

## Strategy Behavior Implemented

A completed daily close below the current point-in-time SMA50 identifies failed
technical-resistance setups early enough to reduce tail loss and improve
risk-adjusted portfolio performance relative to an otherwise identical
six-month no-stop baseline.

## Configuration Delta

TC-002 changes only the portfolio-policy exit behavior from TC-001's
full-position +5.21% comparison baseline. Entry selection remains monthly.
Active positions are monitored after every completed daily session, including
the entry session. A strict `adjusted_close < sma_50` signal liquidates at the
next session's adjusted open. This is a below-state test, not an
above-to-below crossing test.

## Evaluation Sensitivities

The claim is weakened if drawdown improvement comes with materially worse
total return, benchmark-relative return, whipsaw rate, or turnover; if results
depend on one current-constituent universe; or if costs eliminate the effect.

## [Static Universe](../../../stages/OPERATIONS.md#universe-resolution-and-universe-models)

[Random S&P 500 Stocks 50 — Universe 1](../../../configuration/universes/random-sp500-50-1.md)

This is a current-universe-biased research sample, not point-in-time S&P 500
membership.

## [Selection Model](../../../stages/OPERATIONS.md#selection-and-selection-models)

[Technical Resistance Score](../../../stages/selection-models/technical-resistance-score.md)

Use `target_count=1` with the descriptor's existing score, eligibility, and
tie-breaking rules.

## [Trigger](../../../stages/OPERATIONS.md#trigger)

[Monthly Allocation](../../../configuration/triggers/monthly-allocation.md)

The monthly trigger controls new selection cycles only. It does not limit
daily monitoring of an active position.

## Entry Rule

Submit the selected order after the monthly decision close and fill at the next
valid session's adjusted open.

## [Portfolio Policy](../../../stages/OPERATIONS.md#portfolio-transitions-and-portfolio-policies)

[Single Position Profit SMA50 Horizon Exit](../../../stages/portfolio-policies/single-position-profit-sma50-horizon-exit.md)

| Parameter | Value |
| --- | --- |
| `profit_return` | `0.0521` |
| `sma_window` | `50` sessions |
| `sma_signal_operator` | `close_below` |
| `sma_signal_execution` | `next_session_open` |
| `maximum_holding_days` | `126` sessions |

## [Execution](../../../stages/OPERATIONS.md#execution-and-execution-models)

[Daily-Bar Frictionless Fractional](../../../stages/execution-models/daily-bar-frictionless-fractional.md)

Use fractional shares, zero fees, zero slippage, immediate settlement, profit
limits at their limit, SMA50 exits at next adjusted open, and horizon exits at
adjusted close.

## [Funding](../../../stages/OPERATIONS.md#funding-profiles)

[Initial 5000 Only](../../../configuration/funding/initial-5000-only.md)

## [Evaluation](../../../stages/OPERATIONS.md#evaluation-plans)

[TC-001 Development and Retrospective Period](../../../configuration/evaluations/technical-resistance-runner/tc-001-development-retrospective.md)

All periods are now development or retrospective evidence because the SMA50
rule was proposed after prior portfolio and trade charts were inspected.

## Benchmarks

- SPY buy and hold over identical reported dates
- Equal-weight random universe 1
- Full position sold at +5.21%, otherwise held through session 126
- Above-to-below SMA50 crossing variant

## Metrics

- total return, CAGR, and maximum drawdown;
- completed trades, win rate, turnover, and exposure;
- SMA50 exit count and next-open gap slippage;
- loss avoided versus foregone recovery after each SMA50 exit;
- whipsaw rate and re-entry frequency;
- SPY-relative and equal-weight-universe-relative return; and
- development and contaminated retrospective results reported separately.

## Output Location

Generated artifacts belong under:

```text
artifacts/stock/backtests/strategies/technical-resistance-runner/robustness/universe-1/full_at_5_21-sma50-exit/
```
