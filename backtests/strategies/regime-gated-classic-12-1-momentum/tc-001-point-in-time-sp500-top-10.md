# TC-001: Point-in-Time S&P 500 Top-10 Monthly Regime Gate

Strategy:
[Regime-Gated Classic 12-1 Momentum](../../../strategies/regime-gated-classic-12-1-momentum.md)

## Configuration Intent

Test once whether the frozen SPY SMA200 cash gate improves the drawdown of the
otherwise identical classic 12-1 top-ten rotation without sacrificing robust
after-cost outperformance.

## Universe

[Point-in-Time S&P 500](../../../stages/universe-models/point-in-time-sp500.md)

## [Selection Model](../../../stages/OPERATIONS.md#selection-and-selection-models)

[Classic 12-1 Momentum SPY SMA200 Gated](../../../stages/selection-models/classic-12-1-momentum-spy-sma200-gated.md)

## Strategy Parameters

None. All behavior is frozen by the strategy and descriptor.

## [Trigger](../../../stages/OPERATIONS.md#trigger)

[Monthly Allocation](../../../configuration/triggers/monthly-allocation.md)

## [Funding](../../../stages/OPERATIONS.md#funding-profiles)

[Initial 5000 Only](../../../configuration/funding/initial-5000-only.md)

## [Portfolio Policy](../../../stages/OPERATIONS.md#portfolio-transitions-and-portfolio-policies)

[Multi Position Target Weight Rotation](../../../stages/portfolio-policies/multi-position-target-weight-rotation.md)

## [Execution](../../../stages/OPERATIONS.md#execution-and-execution-models) and Accounting

[IBKR Cash T+1](../../../stages/execution-models/ibkr-cash-t-plus-one.md)

Report the zero-cost declared model and a separate 10 bps plus $1/order
sensitivity.

## [Evaluation](../../../stages/OPERATIONS.md#evaluation-plans)

[TC-001 Frozen Confirmation](../../../configuration/evaluations/regime-gated-classic-12-1-momentum/tc-001-frozen-confirmation.md)

## Benchmarks

- frozen ungated classic 12-1 top-ten rotation;
- SPY buy and hold;
- VFMO buy and hold; and
- dated equal-weight eligible universe.

## Metrics

- CAGR, total return, maximum drawdown, and time underwater;
- rolling 12-month excess return and positive-excess rate;
- calendar-year and ticker profit concentration;
- turnover, trade count, cash exposure, and cost sensitivity;
- gate-open/closed counts; and
- candidate coverage and exclusions.

## Output Location

```text
artifacts/stock/backtests/strategies/regime-gated-classic-12-1-momentum/tc-001/
```
