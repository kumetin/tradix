# Regime-Gated Classic 12-1 Momentum Confirmation

## Experiment ID

`regime-gated-classic-12-1-momentum-confirmation`

## Status

`rejected`

## Hypothesis

The frozen monthly SPY SMA200 gate will improve maximum drawdown by at least
five percentage points versus the ungated top-ten rotation while retaining
after-cost CAGR at least three percentage points above both SPY and VFMO.

## Reference Configuration

[TC-001: Point-in-Time S&P 500 Top-10 Monthly Regime Gate](../../backtests/strategies/regime-gated-classic-12-1-momentum/tc-001-point-in-time-sp500-top-10.md)

## Declared Deltas

Relative to the completed ungated run, add only a completed-session SPY
close-at-or-above-SMA200 gate. Emit cash intent when closed. No other signal,
target, cadence, portfolio,
[execution](../../stages/OPERATIONS.md#execution-and-execution-models), or data
rule changes.

## Success Criteria

All are required:

1. Maximum drawdown improves by at least five percentage points versus the
   frozen ungated zero-cost run.
2. The 10 bps plus $1/order sensitivity has CAGR at least three percentage
   points above the stronger of SPY and VFMO.
3. Both gross and after-cost terminal values exceed SPY and VFMO.
4. Mean rolling 12-month excess return is positive versus SPY and VFMO, with
   positive excess in at least 60% of observations.
5. Average dated candidate coverage is at least 95%.
6. No ticker or calendar period supplies half of total profit.
7. The exact frozen scenario is executed once; failed criteria are not tuned
   and retested on this window.

## Run Index

| Status | Configuration | Artifact |
| --- | --- | --- |
| Completed | `1e54a555`; zero-cost declared execution model | [`20260723-220926Z__post-validation-confirmation__1e54a555`](../../artifacts/stock/backtests/strategies/regime-gated-classic-12-1-momentum/tc-001/20260723-220926Z__post-validation-confirmation__1e54a555/) |
| Completed sensitivity | `a24c465f`; 10 bps slippage and $1 per order | [`20260723-221028Z__post-validation-confirmation__a24c465f`](../../artifacts/stock/backtests/strategies/regime-gated-classic-12-1-momentum/tc-001/20260723-221028Z__post-validation-confirmation__a24c465f/) |

## Results

| Series | CAGR | Total return | Maximum drawdown | Time underwater |
| --- | ---: | ---: | ---: | ---: |
| Gated strategy, zero cost | 10.31% | 71.37% | -30.32% | 1,363 days |
| Gated strategy, 10 bps + $1/order | 5.86% | 36.69% | -36.06% | 1,463 days |
| Ungated strategy, zero cost | 26.95% | 270.58% | -29.76% | 630 days |
| SPY | 14.93% | 114.63% | -24.50% | 708 days |
| VFMO | 14.17% | 106.94% | -25.80% | 815 days |

The gate was open at 54 of 67 decision cutoffs and closed at 13. Mean rolling
12-month excess return was -2.88 percentage points versus SPY and -2.73 points
versus VFMO. The positive-excess rates were 40.00% and 36.36%.

The zero-cost run also failed concentration: the partial 2026 calendar period
supplied 56.72% of profit. Under costs it supplied 81.65%. No individual
ticker supplied half of profit. The sensitivity made 802 orders, paid $802 in
modeled fees, and traded gross notional equal to 36.13 times initial capital.

## Findings

The monthly gate did not avoid the baseline's worst drawdown and missed a
material portion of the subsequent rebound. It reduced equity exposure, but
the timing loss overwhelmed that benefit. The result is worse than the
ungated strategy and both external benchmarks on return, drawdown, time
underwater, and rolling excess return.

The 200-session gate was frozen before this run. No alternative SMA, buffer,
confirmation count, daily gate, or re-entry rule was tried after inspection.

## Decision

Reject the strategy. It failed every primary economic criterion other than
average candidate coverage and individual-ticker concentration. Do not tune
another market-trend gate on the consumed 2021-2026 window.
