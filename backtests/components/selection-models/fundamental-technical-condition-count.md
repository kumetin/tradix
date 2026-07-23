# Fundamental Technical Condition-Count Benchmark

## Component Under Test

Component type: [`selection-model`](../../../stages/selection-models/README.md)

[Fundamental Technical Momentum](../../../stages/selection-models/fundamental-technical-momentum.md)

## Question

Do forward outcomes improve monotonically as more of the model's eight
point-in-time conditions are true, even when the strict eight-condition
conjunction is too selective?

## Backtest Type

`isolated component backtest`

## Direct Input/Output Contract

Input is each dated candidate's eight boolean feature values. Complete rows are
assigned a true-condition count from zero through eight and an exact condition
signature. Incomplete rows are reported separately and receive no count.
Output is dated count/signature cohorts and their later market outcomes.

## Outcome Model

Use next-session adjusted open as the reference and adjusted-close returns plus
maximum adverse/favorable excursion at 21, 63, 126, 252, and 378 valid
sessions. No
[portfolio policy](../../../stages/OPERATIONS.md#portfolio-transitions-and-portfolio-policies)
or
[execution model](../../../stages/OPERATIONS.md#execution-and-execution-models)
is applied.

## Aggregation

Equal-weight securities within each universe/date/count cohort, then
equal-weight dated cohort observations when computing count-level summaries.
Compare with SPY and the dated equal-weight candidate universe. Report exact
condition combinations separately and measure adjacent-count monotonicity.

## Metrics

- complete and incomplete evidence coverage;
- observation and dated-cohort counts;
- mean/median return and adverse/favorable excursion;
- excess return versus SPY and the dated equal-weight universe;
- positive-return and SPY-beating rates;
- adjacent-count increases and count/return rank correlation; and
- exact-signature frequency, return, and benchmark-relative return.

## Output Location

Store configuration, candidate classifications, dated cohort outcomes,
count/signature summaries, monotonicity results, and an execution report under:

```text
artifacts/stock/backtests/components/selection-models/fundamental-technical-condition-count/<run-directory>/
```
