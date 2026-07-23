# TC-002: 2015-2020 Temporal Replication

Strategy:
[Classic 12-1 Momentum Rotation](../../../strategies/classic-12-1-momentum-rotation.md)

## Configuration Intent

Replay the exact TC-001 top-ten monthly portfolio over an earlier point-in-time
S&P 500 interval. No signal, target-count, cadence, gate, weighting, or
portfolio-policy change is permitted.

## Universe

[Point-in-Time S&P 500](../../../stages/universe-models/point-in-time-sp500.md)

## [Selection Model](../../../stages/OPERATIONS.md#selection-and-selection-models)

[Classic 12-1 Momentum](../../../stages/selection-models/classic-12-1-momentum.md)

## Strategy Parameters

None.

## [Trigger](../../../stages/OPERATIONS.md#trigger)

[Monthly Allocation](../../../configuration/triggers/monthly-allocation.md)

## [Funding](../../../stages/OPERATIONS.md#funding-profiles)

[Initial 5000 Only](../../../configuration/funding/initial-5000-only.md)

## [Portfolio Policy](../../../stages/OPERATIONS.md#portfolio-transitions-and-portfolio-policies)

[Multi Position Target Weight Rotation](../../../stages/portfolio-policies/multi-position-target-weight-rotation.md)

## [Execution](../../../stages/OPERATIONS.md#execution-and-execution-models) and Accounting

[IBKR Cash T+1](../../../stages/execution-models/ibkr-cash-t-plus-one.md)

Run both the zero-cost descriptor and a 10 bps plus $1/order sensitivity.

## [Evaluation](../../../stages/OPERATIONS.md#evaluation-plans)

[TC-002 2015-2020 Temporal Replication](../../../configuration/evaluations/classic-12-1-momentum-rotation/tc-002-2015-2020-replication.md)

## Benchmarks

- SPY over the full identical window;
- VFMO from its actual 2018 inception only; and
- dated equal-weight eligible universe.

## Metrics

- total return, CAGR, volatility, Sharpe, drawdown, and time underwater;
- calendar-year and ticker concentration;
- rolling 12-month benchmark excess;
- turnover, trade count, and cost sensitivity; and
- candidate coverage and explicit exclusions.

## Output Location

```text
artifacts/stock/backtests/strategies/classic-12-1-momentum-rotation/tc-002/
```
