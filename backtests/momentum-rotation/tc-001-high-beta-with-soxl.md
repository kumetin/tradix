# TC-001: High-Beta Universe With SOXL

Strategy: [Momentum Rotation](../../strategies/momentum-rotation.md)

## Edge Being Tested

This test case checks whether monthly new-money allocation into the strongest eligible high-beta ticker can outperform a simpler static allocation over the same period.

The expected edge has three parts:

- Favor assets with strong intermediate momentum by ranking eligible tickers on trailing 126-trading-day return.
- Avoid the most damaged trends by requiring price or medium-term trend strength above the long-term trend, plus a drawdown no worse than `-45%`.
- Improve entries by waiting for a short pullback, using a 4-down setup before buying with new monthly cash.

The test intentionally does not sell prior holdings. It is testing whether rotating only new contributions is enough to capture momentum while reducing churn, not whether a fully rebalanced momentum portfolio works.

## Universe

[High Beta With SOXL](../../universes/high-beta-with-soxl.md)

## Selection Model

[SMA Drawdown Trailing Return](../../selection-models/sma-drawdown-trailing-return.md)

| Parameter | Value |
| --- | --- |
| `medium_sma_window` | `50` trading days |
| `long_sma_window` | `200` trading days |
| `rolling_high_window` | `252` trading days |
| `max_drawdown` | `-45%` |
| `ranking_return_window` | `126` trading days |

## Strategy Parameters

| Parameter | Value |
| --- | --- |
| `entry_down_days` | `4` |
| `entry_fallback` | Buy at month-end adjusted open |

## Schedule

[Monthly New Cash](../../schedules/monthly-new-cash.md)

## Funding

[Initial 5000 Monthly 100](../../funding-profiles/initial-5000-monthly-100.md)

## Portfolio Policy

[New Money Only No Selling](../../portfolio-policies/new-money-only-no-selling.md)

## Execution and Accounting

[Frictionless Fractional](../../execution-models/frictionless-fractional.md)

## Evaluation

[TC-001 Full Period](../../evaluations/momentum-rotation/tc-001-full-period.md)

## Benchmarks

- `SPY` buy and hold
- Equal-weight [High Beta With SOXL](../../universes/high-beta-with-soxl.md)
  universe
