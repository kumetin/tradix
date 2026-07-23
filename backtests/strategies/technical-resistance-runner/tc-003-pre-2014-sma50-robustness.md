# TC-003: Pre-2014 SMA50 Exit Robustness

Strategy: [Technical Resistance Runner](../../../strategies/technical-resistance-runner.md)

## Configuration Intent

Whether the frozen daily below-SMA50 portfolio policy improves the strategy's
tail control without destroying return in the previously unrun 2007–2009
crisis and 2010–2013 recovery regimes.

## Configuration Delta

Compare the same monthly selector and full-position +5.21% target with and
without the daily SMA50 exit. Only the portfolio-policy exit behavior varies.

## [Static Universe](../../../stages/OPERATIONS.md#universe-resolution-and-universe-models)

[Random S&P 500 Stocks 50 — Universe 1](../../../configuration/universes/random-sp500-50-1.md)

Membership is current-constituent biased and projected backward.

## [Selection Model](../../../stages/OPERATIONS.md#selection-and-selection-models)

[Technical Resistance Score](../../../stages/selection-models/technical-resistance-score.md)

## [Trigger](../../../stages/OPERATIONS.md#trigger)

[Monthly Allocation](../../../configuration/triggers/monthly-allocation.md)

The trigger controls new selection cycles; the policy monitors active
positions daily.

## [Portfolio Policy](../../../stages/OPERATIONS.md#portfolio-transitions-and-portfolio-policies)

[Single Position Profit SMA50 Horizon Exit](../../../stages/portfolio-policies/single-position-profit-sma50-horizon-exit.md)

Compare `full_at_5_21_sma50_exit` against `full_at_5_21`.

## [Execution](../../../stages/OPERATIONS.md#execution-and-execution-models)

[Daily-Bar Frictionless Fractional](../../../stages/execution-models/daily-bar-frictionless-fractional.md)

## [Funding](../../../stages/OPERATIONS.md#funding-profiles)

[Initial 5000 Only](../../../configuration/funding/initial-5000-only.md)

## [Evaluation](../../../stages/OPERATIONS.md#evaluation-plans)

[TC-003 Pre-2014 Regimes](../../../configuration/evaluations/technical-resistance-runner/tc-003-pre-2014-regimes.md)

## Benchmarks

- SPY buy and hold over each identical window
- Equal-weight universe 1 among constituents with price history in the window
- Frozen no-SMA50 +5.21% target baseline

## Metrics

- total return, CAGR, maximum drawdown, and win rate;
- SMA50 and profit-target exit counts;
- SPY-relative and equal-weight-universe-relative return;
- eligible historical constituent count; and
- each fixed regime reported separately.

## Output Location

```text
artifacts/stock/backtests/strategies/technical-resistance-runner/untried-windows/
```
