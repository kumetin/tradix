# Classic 12-1 Momentum Rotation Profitability

## Experiment ID

`classic-12-1-momentum-rotation-profitability`

## Status

`completed_not_promoted`

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

| Status | Configuration | Artifact |
| --- | --- | --- |
| Superseded | `d52349b5`; incomplete tape-loading universe and pre-VFMO reporting | [`20260723-215350Z__post-validation-confirmation__d52349b5`](../../artifacts/stock/backtests/strategies/classic-12-1-momentum-rotation/tc-001/20260723-215350Z__post-validation-confirmation__d52349b5/) |
| Superseded | `e60d12b9`; corrected loader but before missing canonical histories were repaired | [`20260723-215727Z__post-validation-confirmation__e60d12b9`](../../artifacts/stock/backtests/strategies/classic-12-1-momentum-rotation/tc-001/20260723-215727Z__post-validation-confirmation__e60d12b9/) |
| Superseded | `2fb7160d`; repaired histories but before mandatory diagnostic outputs | [`20260723-220358Z__post-validation-confirmation__2fb7160d`](../../artifacts/stock/backtests/strategies/classic-12-1-momentum-rotation/tc-001/20260723-220358Z__post-validation-confirmation__2fb7160d/) |
| Completed | `2fb7160d`; zero-cost declared execution model | [`20260723-220547Z__post-validation-confirmation__2fb7160d`](../../artifacts/stock/backtests/strategies/classic-12-1-momentum-rotation/tc-001/20260723-220547Z__post-validation-confirmation__2fb7160d/) |
| Completed sensitivity | `565e4b5d`; 10 bps slippage and $1 per order | [`20260723-220615Z__post-validation-confirmation__565e4b5d`](../../artifacts/stock/backtests/strategies/classic-12-1-momentum-rotation/tc-001/20260723-220615Z__post-validation-confirmation__565e4b5d/) |

## Results

The repaired zero-cost run produced:

| Series | CAGR | Total return | Maximum drawdown | Maximum time underwater |
| --- | ---: | ---: | ---: | ---: |
| Strategy | 26.95% | 270.58% | -29.76% | 630 days |
| SPY | 14.93% | 114.63% | -24.50% | 708 days |
| VFMO | 14.17% | 106.94% | -25.80% | 815 days |
| Dated equal-weight eligible universe | 12.54% | 89.69% | -20.63% | 699 days |

The 55 rolling 12-month observations had mean excess returns of 13.42
percentage points versus SPY, 13.57 points versus VFMO, and 17.80 points
versus the dated equal-weight eligible universe. Positive rolling-excess rates
were respectively 76.36%, 89.09%, and 89.09%.

Average dated candidate coverage was 95.43%, with a 91.00% minimum and 98.21%
maximum. Every candidate received an eligibility decision. Remaining missing
histories and integrity exclusions are retained in `coverage.csv`; missing
outcomes were not forward-filled.

The plausible-cost sensitivity remained profitable:

| Series | CAGR | Total return | Maximum drawdown | Maximum time underwater |
| --- | ---: | ---: | ---: | ---: |
| Strategy, 10 bps plus $1/order | 22.07% | 198.85% | -30.60% | 1,060 days |

The zero-cost run made 980 orders and traded gross notional equal to 58.97
times initial capital. The cost run made 955 orders, paid $955 in modeled
fees, and traded 50.95 times initial capital.

No ticker supplied half of total profit. The largest zero-cost contributors
were MU (17.30%), STX (13.26%), WDC (12.90%), PLTR (9.29%), and LRCX (9.23%).
However, the partial 2026 calendar period supplied 54.99% of total zero-cost
profit and 59.08% of cost-adjusted profit, failing the preregistered
calendar-period concentration criterion.

## Findings

The full portfolio expression is much stronger than the earlier component
validation's average top-ten forward outcomes: it substantially outperformed
SPY, VFMO, and the dated eligible universe in this post-validation window,
including under explicit friction. The T+1 implementation kept sale proceeds
in account equity while preventing their reuse until the following session.
Signals used the last completed monthly session and orders used later adjusted
opens.

The result is nevertheless concentrated in the most recent partial year and
in a related memory/storage momentum cluster. Its drawdown exceeded all three
benchmarks. The classic selector also failed its preregistered 2016-2020
cross-sectional ordering test. These facts prevent the attractive portfolio
return from serving as robust promotion evidence.

Earlier run returns were superseded after the driver exposed incomplete
membership-tape loading and missing canonical histories. Fifty recoverable
histories were persisted and features regenerated before the completed runs.
Provider-unavailable delisted or renamed histories remain explicit coverage
limitations.

## Decision

Do not promote this scenario as the final strategy. Preserve it as the leading
price-only challenger because it passes most portfolio-level criteria and
beats both SPY and VFMO by a wide margin, but it fails the preregistered
calendar-period concentration requirement, has worse maximum drawdown than
the benchmarks, and lacks consistent supporting evidence from the independent
component validation.

## Follow-up

Do not tune target count, lookback, skip, or cadence on the consumed
2021-2026 window. Use this frozen scenario as a comparator for separately
specified strategies with independently motivated risk controls. Any promoted
successor must demonstrate value on a new validation schedule and a reserved
holdout or genuinely different point-in-time market.
