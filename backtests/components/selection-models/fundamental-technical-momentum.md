# Fundamental Technical Momentum [Selection](../../../stages/OPERATIONS.md#selection-and-selection-models) Benchmark

## Component Under Test

Component type: [`selection-model`](../../../stages/selection-models/README.md)

[Fundamental Technical Momentum](../../../stages/selection-models/fundamental-technical-momentum.md)

## Question

Does simultaneous point-in-time fundamental improvement and confirmed market
demand identify stocks with better forward outcomes than simpler fundamental,
technical, and universe baselines?

## Backtest Type

`isolated component backtest`

## Direct Input/Output Contract

Input is a decision cutoff, point-in-time candidates, and the latest feature
rows knowable at that cutoff. Output is per-candidate eligibility, deterministic
ranking, and equal-weight targets. Score outputs against later outcomes without
running a complete portfolio strategy.

## Variants

- full eight-condition conjunction;
- fundamental-only four-condition filter;
- technical/demand-only four-condition filter;
- each leave-one-condition-out variant; and
- target counts `1`, `5`, `10`, and `20`.

Threshold variants must be declared in an experiment before their results are
inspected.

## Outcome Model

Use next-session adjusted open as the observable outcome reference, without
applying an [execution model](../../../stages/OPERATIONS.md#execution-and-execution-models).
Measure
adjusted-close returns and maximum adverse/favorable excursion over 21, 63,
126, 252, and 378 valid sessions. Warm-up rows initialize features but are
excluded from metrics.

## [Evaluation](../../../stages/OPERATIONS.md#evaluation-plans) Matrix

Concrete development, validation, regime, and locked-holdout windows are
deliberately delegated to an experiment record. Do not reuse another
strategy's evaluation dates implicitly.

## Metrics

- hit rate above zero and above SPY;
- mean and median forward return;
- excess return versus SPY and dated equal-weight universe;
- rank-bucket monotonicity;
- eligible coverage, missing-evidence exclusions, and fallback rate;
- result concentration by ticker, sector, year, and regime; and
- turnover implied by consecutive target sets.

## Baselines

Use SPY, the dated equal-weight candidate universe, unfiltered candidates,
fundamental-only, technical/demand-only, and leave-one-condition-out variants.

## Interpretation Rules

Do not promote from development performance alone. Reuse requires consistent
benchmark-relative improvement across multiple horizons and regimes, followed
by a locked holdout with point-in-time membership. A high raw hit rate without
positive excess return, adequate coverage, and acceptable concentration is
insufficient.

## Output Location

Store immutable run configuration, eligibility/ranking output, forward
outcomes, aggregate summaries, and an execution report under:

```text
artifacts/stock/backtests/components/selection-models/fundamental-technical-momentum/<run-directory>/
```
