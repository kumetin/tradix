# Fundamental Technical Seven-Condition Validation

## Experiment ID

`fundamental-technical-seven-condition-validation`

## Status

`rejected_for_promotion`

## Hypothesis

Removing abnormal up-volume as an eligibility requirement yields a
seven-condition selector with positive benchmark-relative forward outcomes in
the unused validation window.

## Reference Configuration

- [Selection model](../../stages/OPERATIONS.md#selection-and-selection-models):
  [`fundamental-technical-momentum-seven-condition`](../../stages/selection-models/fundamental-technical-momentum-seven-condition.md)
- Component protocol:
  [`fundamental-technical-seven-condition-validation`](../../backtests/components/selection-models/fundamental-technical-seven-condition-validation.md)
- [Evaluation plan](../../stages/OPERATIONS.md#evaluation-plans):
  [`fundamental-technical-seven-condition-validation`](../../configuration/evaluations/selection-models/fundamental-technical-seven-condition-validation.md)

## Declared Deltas

The model removes only `is_high_relative_volume` from eligibility. Compare
target counts 1, 5, 10, and 20 against the strict selector and unfiltered rank
across the five existing random universes.

## Success Criteria

For target count 10, the seven-condition model must generate at least 30
forward observations and have positive mean excess return versus both SPY and
the dated equal-weight universe at 126 and 252 sessions. Both excess returns
must be positive in at least three of five universes at each primary horizon.
No single ticker may contribute more than 20% of observations.

## Run Index

| Status | Configuration | Artifact |
| --- | --- | --- |
| Completed | `b8fe7bfa` | [`20260723-124501Z__unused-2025h1__b8fe7bfa`](../../artifacts/stock/backtests/components/selection-models/fundamental-technical-seven-condition-validation/20260723-124501Z__unused-2025h1__b8fe7bfa/) |

## Results

At target count 10, the seven-condition model produced 63 observations from
six unique tickers:

| Horizon | Mean return | Excess vs SPY | Excess vs universe | Positive rate |
| ---: | ---: | ---: | ---: | ---: |
| 21 | 4.41% | 1.92% | 2.59% | 73.02% |
| 63 | 12.72% | 4.53% | 6.66% | 73.02% |
| 126 | 16.25% | 2.37% | 3.67% | 73.02% |
| 252 | 18.09% | -6.16% | -13.76% | 60.32% |

Only one universe was positive against both benchmarks at 126 sessions, and
only one was positive against both at 252 sessions. One universe generated no
seven-condition observations. CTAS contributed 33.33% of all observations,
above the preregistered 20% concentration ceiling.

The strict model produced only four observations. The unfiltered rank produced
1,200 observations and exceeded the seven-condition model by 15.07 percentage
points of mean return at 252 sessions.

This diagnostic does not apply a
[portfolio policy](../../stages/OPERATIONS.md#portfolio-transitions-and-portfolio-policies)
or separate
[execution model](../../stages/OPERATIONS.md#execution-and-execution-models).

## Findings

Removing abnormal up-volume improved coverage and short-horizon aggregate
outcomes, but it did not produce a stable long-horizon selector. The positive
126-session aggregate was not consistent across universes and was concentrated
in repeated observations of a few tickers. At 252 sessions the model
underperformed both benchmarks materially.

The validation window is now inspected and cannot be reused as a clean test
for subsequent rule changes.

## Decision

Do not promote the seven-condition selector. It failed benchmark consistency,
252-session excess-return, and concentration criteria.

## Follow-up

Stop conjunction removal based on this validation family. Before defining
another selector, investigate why the unfiltered momentum rank outperformed
the filtered models and whether the fundamental conditions are better used as
continuous ranking features rather than hard eligibility gates. Any new model
requires a new evaluation plan.
