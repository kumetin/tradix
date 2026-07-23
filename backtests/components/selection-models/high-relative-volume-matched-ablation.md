# High Relative Volume Matched Ablation

## Component Under Test

Component type: [`selection-model`](../../../stages/selection-models/README.md)

[Fundamental Technical Momentum](../../../stages/selection-models/fundamental-technical-momentum.md)

## Question

Among complete-evidence candidates satisfying the other seven model conditions,
does the abnormal up-volume condition improve forward outcomes?

## Backtest Type

`isolated component backtest`

## Direct Input/Output Contract

Input is the dated complete-evidence condition/outcome tape from the
condition-count diagnostic. Within each universe/date cell, candidates passing
the other seven conditions are divided by `is_high_relative_volume`. Output is
a matched cell-level treated-minus-control outcome difference. Cells without
both groups are excluded and reported.

## Outcome Model

Use the source diagnostic's next-session adjusted-open reference and
adjusted-close outcomes at 21, 63, 126, 252, and 378 valid sessions. No
[portfolio policy](../../../stages/OPERATIONS.md#portfolio-transitions-and-portfolio-policies)
or [execution model](../../../stages/OPERATIONS.md#execution-and-execution-models)
is applied.

## Metrics

- matched cell, treated-observation, control-observation, and ticker counts;
- treated and control mean return, hit rate, and adverse/favorable excursion;
- paired mean and median return difference;
- fraction of cells favoring the volume condition;
- deterministic date-cell bootstrap 95% interval; and
- consistency by universe and
  [evaluation window](../../../stages/OPERATIONS.md#evaluation-plans).

## Interpretation Rules

This is a contemporaneous matched cohort comparison, not causal proof. The
volume condition is useful only if treated-minus-control performance is
positive across relevant horizons and not driven by a few cells or tickers.

## Output Location

Store configuration, matched cells, aggregate and subgroup summaries, bootstrap
results, exclusions, and an execution report under:

```text
artifacts/stock/backtests/components/selection-models/high-relative-volume-matched-ablation/<run-directory>/
```
