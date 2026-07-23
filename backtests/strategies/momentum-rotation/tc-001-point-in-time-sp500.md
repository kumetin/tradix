# TC-001: Point-in-Time S&P 500 New-Money Allocation

Strategy: [Momentum Rotation](../../../strategies/momentum-rotation.md)

## Configuration Intent

### Strategy Behavior Implemented

Within point-in-time S&P 500 membership, the strongest intermediate-momentum
member whose broader trend remains intact is expected to outperform weaker
members over the next monthly allocation cycle. A four-down-close pullback is
expected to improve entry quality without erasing that continuation advantage.

The expected edge has three parts:

- Favor assets with strong intermediate momentum by ranking eligible tickers on trailing 126-trading-day return.
- Avoid the most damaged trends by requiring price or medium-term trend strength above the long-term trend, plus a drawdown no worse than `-45%`.
- Improve entries by waiting for a short pullback, using a 4-down setup before buying with new monthly cash.

### Portfolio Expression

The test intentionally does not sell prior holdings. It asks whether the signal
can improve allocation of new contributions; accumulation is not part of the
market-predictability thesis and must not be mistaken for evidence that rotation
itself is superior.

### Evaluation Sensitivities

The claim is weakened if top-ranked selections fail to outperform the
equal-weight dated universe, if trend/drawdown eligibility does not improve on
momentum-only [selection](../../../stages/OPERATIONS.md#selection-and-selection-models), or if pullback entry underperforms immediate entry
after missed opportunities are included.

## Universe

[Point-in-Time S&P 500](../../../stages/universe-models/point-in-time-sp500.md)

## Selection Model

[SMA Drawdown Trailing Return](../../../stages/selection-models/sma-drawdown-trailing-return.md)

| Parameter | Value |
| --- | --- |
| `medium_sma_window` | `50` trading days |
| `long_sma_window` | `200` trading days |
| `rolling_high_window` | `252` trading days |
| `max_drawdown` | `-45%` |
| `ranking_return_window` | `126` trading days |
| `fallback_ticker` | `SPY` |

## Strategy Parameters

| Parameter | Value |
| --- | --- |
| `entry_down_days` | `4` |
| `entry_fallback` | Buy at month-end adjusted open |

## [Trigger](../../../stages/OPERATIONS.md#trigger)

[Monthly Allocation](../../../configuration/triggers/monthly-allocation.md)

## [Funding](../../../stages/OPERATIONS.md#funding-profiles)

[Initial 5000 Monthly 100](../../../configuration/funding/initial-5000-monthly-100.md)

## [Portfolio Policy](../../../stages/OPERATIONS.md#portfolio-transitions-and-portfolio-policies)

[New Money Only No Selling](../../../stages/portfolio-policies/new-money-only-no-selling.md)

## [Execution](../../../stages/OPERATIONS.md#execution-and-execution-models) and Accounting

[Frictionless Fractional](../../../stages/execution-models/frictionless-fractional.md)

## [Evaluation](../../../stages/OPERATIONS.md#evaluation-plans)

[TC-001 Full Period](../../../configuration/evaluations/momentum-rotation/tc-001-full-period.md)

## Benchmarks

- `SPY` buy and hold
- Equal-weight point-in-time S&P 500 universe
