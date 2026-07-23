# Continuous Fundamental Momentum Validation

Isolated [selection](../../../stages/OPERATIONS.md#selection-and-selection-models)
benchmark.

## Component Under Test

Component type: [`selection-model`](../../../stages/selection-models/README.md)

[Continuous Fundamental Momentum](../../../stages/selection-models/continuous-fundamental-momentum.md)

## Question

Does a frozen continuous fundamental-plus-momentum rank outperform
momentum-only ranking and the seven-condition selector on a fresh window?

## Backtest Type

`isolated component backtest`

## Direct Input/Output Contract

Input is each weekly dated universe and its point-in-time feature rows. Output
is data-sufficiency eligibility, deterministic ranking, and equal-weight
targets. Future bars score outputs only after selection.

## Variants

Compare continuous fundamental momentum, momentum-only ranking, and the frozen
seven-condition selector at target counts 5, 10, and 20.

## Outcome Model

Use next-session adjusted open and adjusted-close outcomes over 21, 63, and 126
valid sessions. No
[portfolio policy](../../../stages/OPERATIONS.md#portfolio-transitions-and-portfolio-policies)
or
[execution model](../../../stages/OPERATIONS.md#execution-and-execution-models)
is applied.

## Metrics

- eligible coverage and selection frequency;
- mean and median forward return;
- excess return versus SPY and dated equal-weight universe;
- positive-return and SPY-beating hit rates;
- adverse/favorable excursion;
- concentration by ticker and universe; and
- paired decision-date difference versus momentum-only ranking.

## Output Location

Store configuration, coverage, outcomes, summaries, paired comparisons, and an
execution report:

```text
artifacts/stock/backtests/components/selection-models/continuous-fundamental-momentum-validation/<run-directory>/
```
