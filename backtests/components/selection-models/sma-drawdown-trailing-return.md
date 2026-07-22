# SMA Drawdown Trailing Return [Selection](../../../stages/OPERATIONS.md#selection-and-selection-models) Benchmark

## Component Under Test

Component type: [`selection-model`](../../../stages/selection-models/README.md)

[SMA Drawdown Trailing Return](../../../stages/selection-models/sma-drawdown-trailing-return.md)

## Question

Does the SMA, drawdown, and trailing-return selector rank candidates by useful
forward return and downside characteristics across different market periods?

## Backtest Type

`isolated component backtest`

## Direct Input/Output Contract

Input: a decision date, a point-in-time candidate set, and feature rows available
before that decision date.

Output: eligibility decisions, ranking scores, ordered candidates, selected
targets and weights, or the declared fallback result.

The benchmark runner scores those outputs against later price outcomes. It does
not apply an entry rule, [portfolio policy](../../../stages/OPERATIONS.md#portfolio-transitions-and-portfolio-policies), [funding](../../../stages/OPERATIONS.md#funding-profiles) schedule, or [execution model](../../../stages/OPERATIONS.md#execution-and-execution-models).

## Variants

| Variant | `medium_sma_window` | `long_sma_window` | `rolling_high_window` | `max_drawdown` | `ranking_return_window` |
| --- | ---: | ---: | ---: | ---: | ---: |
| Current profile default | `50` | `200` | `252` | `-45%` | `126` |
| Faster momentum | `50` | `200` | `252` | `-45%` | `63` |
| Slower momentum | `50` | `200` | `252` | `-45%` | `252` |
| Stricter drawdown | `50` | `200` | `252` | `-30%` | `126` |

## [Evaluation](../../../stages/OPERATIONS.md#evaluation-plans) Matrix

- [TC-001 Full Period](../../../configuration/evaluations/momentum-rotation/tc-001-full-period.md)
- Add separate bull, bear, recovery, sideways, validation, and locked holdout
  profiles before treating the selector as robust.

## Metrics

| Metric | Reason |
| --- | --- |
| Rank correlation with forward return | Measures whether ordering quality persists out of sample. |
| Top-selection excess forward return | Compares selected candidates with the same-date candidate baseline. |
| Hit rate and return monotonicity by rank bucket | Checks whether better ranks correspond to better outcomes. |
| Forward adverse excursion | Tests whether eligibility filters avoid subsequent downside. |
| Fallback rate | Shows how often the model fails to find an eligible ticker. |
| Selection turnover | Measures output stability without imposing portfolio behavior. |

## Baselines

- Same-date equal-weight forward return of the candidate set.
- Random ranking over the same dated candidates.
- A simple trailing-return-only selector over the same universe, when available.

## Interpretation Rules

Treat the profile as reusable only if ranking quality and top-selection excess
return persist after warm-up exclusion across more than one evaluation period
without relying on one outlier ticker or market regime.

Treat weak benchmark-relative return, high fallback rate, or unstable parameter
rankings as evidence that the selector should remain experimental.

## Output Location

Generated artifacts should live under:

```text
artifacts/stock/backtests/components/selection-models/sma-drawdown-trailing-return/
```
