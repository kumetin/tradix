# Classic 12-1 Momentum Rotation Profitability

## Experiment ID

`classic-12-1-momentum-rotation-profitability`

## Status

`ready`

## Hypothesis

The frozen classic 12–1 selector can be expressed as a diversified monthly
rotation portfolio that compounds the initial capital after
[execution](../../stages/OPERATIONS.md#execution-and-execution-models) drag
and adds value beyond passive and cross-sectional baselines during the
post-validation
[evaluation](../../stages/OPERATIONS.md#evaluation-plans) period.

## Reference Configuration

[TC-001: Point-in-Time S&P 500 Top-10 Monthly Rotation](../../backtests/strategies/classic-12-1-momentum-rotation/tc-001-point-in-time-sp500-top-10.md)

## Declared Deltas

None. This is the frozen baseline strategy scenario. No parameter sweep is
authorized.

## Success Criteria

Before inspecting the strategy results, success requires all of the following:

1. Positive total return and CAGR after modeled execution drag.
2. Terminal value above the equal-weight eligible-universe benchmark.
3. Positive mean rolling 12-month excess return versus that universe.
4. Positive excess return versus SPY over the full evaluation window.
5. Positive strategy return in more calendar years than negative years.
6. No single ticker or calendar year contributes more than half of total
   portfolio profit.
7. Candidate coverage averages at least 95%, with every exclusion reported.
8. Performance remains positive under a separately reported plausible
   commission-and-slippage sensitivity.

Maximum drawdown, turnover, and time under water are mandatory decision
metrics, not criteria that may be omitted when returns pass.

## Run Index

Pending.

## Results

Pending.

## Findings

Pending.

## Decision

Pending.

## Follow-up

If the frozen scenario passes, test it on a genuinely untouched later period
or a different point-in-time market before considering paper trading. If it
fails, preserve the run and do not tune target count, gates, or timing on this
same confirmation window.
