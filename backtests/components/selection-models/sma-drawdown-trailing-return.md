# SMA Drawdown Trailing Return Selection Benchmark

## Component Under Test

Component type: [`selection-model`](../../../selection-models/README.md)

[SMA Drawdown Trailing Return](../../../selection-models/sma-drawdown-trailing-return.md)

## Question

Does the SMA, drawdown, and trailing-return selector produce a useful ranking
signal across different market periods when the [universe](../../../universes/README.md),
entry rule, [portfolio policy](../../../portfolio-policies/README.md),
[execution model](../../../execution-models/README.md), and
[funding profile](../../../funding-profiles/README.md) are held fixed?

## Backtest Type

`harnessed component backtest`

## Fixed Harness

| Layer | Profile |
| --- | --- |
| [Strategy](../../../strategies/README.md) | [Momentum Rotation](../../../strategies/momentum-rotation.md) |
| [Trigger](../../../triggers/README.md) | [Monthly Allocation](../../../triggers/monthly-allocation.md) |
| [Universe](../../../universes/README.md) | [High Beta With SOXL](../../../universes/high-beta-with-soxl.md) |
| [Portfolio Policy](../../../portfolio-policies/README.md) | [New Money Only No Selling](../../../portfolio-policies/new-money-only-no-selling.md) |
| [Execution Model](../../../execution-models/README.md) | [Frictionless Fractional](../../../execution-models/frictionless-fractional.md) |
| [Funding Profile](../../../funding-profiles/README.md) | [Initial 5000 Monthly 100](../../../funding-profiles/initial-5000-monthly-100.md) |

## Variants

| Variant | `medium_sma_window` | `long_sma_window` | `rolling_high_window` | `max_drawdown` | `ranking_return_window` |
| --- | ---: | ---: | ---: | ---: | ---: |
| Current profile default | `50` | `200` | `252` | `-45%` | `126` |
| Faster momentum | `50` | `200` | `252` | `-45%` | `63` |
| Slower momentum | `50` | `200` | `252` | `-45%` | `252` |
| Stricter drawdown | `50` | `200` | `252` | `-30%` | `126` |

## Evaluation Matrix

- [TC-001 Full Period](../../../evaluations/momentum-rotation/tc-001-full-period.md)
- Add separate bull, bear, recovery, sideways, validation, and locked holdout
  profiles before treating the selector as robust.

## Metrics

| Metric | Reason |
| --- | --- |
| Total return and CAGR | Measures whether the selector adds return under the fixed harness. |
| Max drawdown | Checks whether the trend and drawdown filters actually reduce downside. |
| Volatility and Sharpe-like return per volatility | Separates raw return from risk taken. |
| Fallback rate | Shows how often the model fails to find an eligible ticker. |
| Selection turnover | Estimates churn pressure before a portfolio policy is applied. |
| Benchmark-relative return | Compares against `SPY` and equal-weight universe exposure. |

## Baselines

- `SPY` buy and hold over the same evaluation windows.
- Equal-weight [High Beta With SOXL](../../../universes/high-beta-with-soxl.md)
  universe over the same evaluation windows.
- A simple trailing-return-only selector over the same universe, when available.

## Interpretation Rules

Treat the profile as reusable only if it beats the equal-weight universe after
warm-up exclusion across more than one evaluation period without relying on one
outlier ticker or one market regime.

Treat weak benchmark-relative return, high fallback rate, or unstable parameter
rankings as evidence that the selector should remain experimental.

## Output Location

Generated artifacts should live under:

```text
artifacts/stock/backtests/components/selection-models/sma-drawdown-trailing-return/
```
