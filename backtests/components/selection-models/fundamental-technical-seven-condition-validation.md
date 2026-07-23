# Fundamental Technical Seven-Condition Validation

Isolated [selection](../../../stages/OPERATIONS.md#selection-and-selection-models)
diagnostic.

## Component Under Test

Component type: [`selection-model`](../../../stages/selection-models/README.md)

[Fundamental Technical Momentum Seven Condition](../../../stages/selection-models/fundamental-technical-momentum-seven-condition.md)

## Question

Does the frozen seven-condition selector produce positive forward
benchmark-relative outcomes in a previously unused validation window?

## Backtest Type

`isolated component backtest`

## Direct Input/Output Contract

Input is each weekly dated universe and point-in-time feature rows. Output is
seven-condition eligibility, deterministic ranking, and equal-weight targets.
Future bars score outputs only after selection.

## Variants

Compare the seven-condition selector, the original strict eight-condition
selector, and unfiltered momentum ranking at target counts 1, 5, 10, and 20.

## Outcome Model

Use next-session adjusted open and adjusted-close outcomes over 21, 63, 126,
and 252 valid sessions. No
[portfolio policy](../../../stages/OPERATIONS.md#portfolio-transitions-and-portfolio-policies)
or [execution model](../../../stages/OPERATIONS.md#execution-and-execution-models)
is applied.

## Metrics

- eligible coverage and selection frequency;
- mean and median forward return;
- excess return versus SPY and dated equal-weight universe;
- positive-return and SPY-beating hit rates;
- adverse/favorable excursion; and
- concentration by ticker and universe.

## Output Location

Store configuration, coverage, outcomes, summaries, and an execution report:

```text
artifacts/stock/backtests/components/selection-models/fundamental-technical-seven-condition-validation/<run-directory>/
```
