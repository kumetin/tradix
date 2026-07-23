# Fundamental Technical Momentum SEC 13F Benchmark

## Experiment ID

`fundamental-technical-momentum-sec-13f`

## Status

`rejected_for_promotion`

## Hypothesis

With filing-date-aware institutional evidence available, the full conjunction
has nonzero coverage and produces better forward returns than SPY, the dated
equal-weight universe, and the declared component ablations.

## Reference Configuration

- [Selection model](../../stages/OPERATIONS.md#selection-and-selection-models):
  [`fundamental-technical-momentum`](../../stages/selection-models/fundamental-technical-momentum.md)
- [Component protocol](../../backtests/components/selection-models/fundamental-technical-momentum.md)
- [Evaluation plan](../../stages/OPERATIONS.md#evaluation-plans):
  [`fundamental-technical-momentum-exploratory`](../../configuration/evaluations/selection-models/fundamental-technical-momentum-exploratory.md)

## Declared Deltas

Relative to the earlier coverage-diagnostic experiment, institutional
accumulation is populated from chronologically replayed SEC Form 13F filings.
The five universes, three exploratory windows, variants, target counts, weekly
cadence, entry reference, and outcome horizons remain unchanged.

## Success Criteria

The full model must have nonzero usable coverage and positive mean excess
return versus both SPY and the equal-weight universe in a majority of
universe/window cells at 126 and 252 sessions. Results must not depend on one
ticker or window. These current-constituent development windows cannot support
promotion without a separately frozen validation and holdout.

## Run Index

| Status | Configuration | Artifact |
| --- | --- | --- |
| Completed | `03b44fe7` | [`20260723-120244Z__exploratory-five-universes__03b44fe7`](../../artifacts/stock/backtests/components/selection-models/fundamental-technical-momentum/20260723-120244Z__exploratory-five-universes__03b44fe7/) |

## Results

At target count 10, the full conjunction generated 38 forward observations
from 36 of 935 weekly universe/window decisions, covering 24 unique tickers.

| Horizon | Mean return | Excess vs SPY | Excess vs universe | Positive-return hit rate |
| ---: | ---: | ---: | ---: | ---: |
| 21 | 0.03% | -1.70% | -1.25% | 42.11% |
| 63 | -1.40% | -4.56% | -4.86% | 55.26% |
| 126 | 4.18% | -2.03% | -2.32% | 57.89% |
| 252 | 9.12% | -1.86% | -1.71% | 57.89% |
| 378 | 12.94% | -8.95% | -8.93% | 71.05% |

The full model beat both benchmarks in 3 of 12 usable universe/window cells at
126 sessions and 5 of 12 at 252 sessions. Approximately 70% of candidate
decision rows lacked at least one required item of evidence. Rank-bucket
monotonicity was not meaningfully measurable: 36 observations were rank 1 and
only two were rank 2.

This component experiment does not apply an
[execution model](../../stages/OPERATIONS.md#execution-and-execution-models).

## Findings

SEC 13F history resolved the earlier institutional-data blocker, but the full
conjunction remained extremely selective and did not deliver positive
benchmark-relative outcomes. Its positive raw returns at longer horizons
largely reflected the rising market rather than selection edge.

The unfiltered ranking baseline outperformed both benchmarks in aggregate,
while the fundamental-only and technical/demand-only filters each
underperformed. This weakens the claim that conjunction filtering adds value
to the existing momentum rank.

## Decision

Do not promote the full selector. The preregistered coverage and
benchmark-relative success criteria were not met.

## Follow-up

Diagnose missing fundamental coverage and benchmark individual conditions
before changing thresholds. Any revised conjunction should be evaluated in a
new experiment and must not treat these exploratory windows as a clean
holdout.
