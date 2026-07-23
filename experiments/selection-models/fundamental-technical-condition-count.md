# Fundamental Technical Condition-Count Diagnostic

## Experiment ID

`fundamental-technical-condition-count`

## Status

`rejected_for_promotion`

## Hypothesis

Forward benchmark-relative outcomes improve as the number of true model
conditions rises from zero through eight.

## Reference Configuration

- [Selection model](../../stages/OPERATIONS.md#selection-and-selection-models):
  [`fundamental-technical-momentum`](../../stages/selection-models/fundamental-technical-momentum.md)
- Component protocol:
  [`fundamental-technical-condition-count`](../../backtests/components/selection-models/fundamental-technical-condition-count.md)
- [Evaluation plan](../../stages/OPERATIONS.md#evaluation-plans):
  [`fundamental-technical-momentum-exploratory`](../../configuration/evaluations/selection-models/fundamental-technical-momentum-exploratory.md)

## Declared Deltas

Use the same five universes, three exploratory windows, weekly cadence, entry
reference, and five horizons as the strict-selector benchmark. Replace binary
all-of eligibility with diagnostic complete-evidence cohorts from zero through
eight true conditions. This does not change the production selector.

## Success Criteria

At 126 and 252 sessions, count-level mean excess return versus both SPY and the
dated equal-weight universe should have positive Spearman correlation with
condition count, at least five of eight adjacent populated count transitions
should improve, and the upper cohorts should not depend on one exact signature
or a small number of dated observations. These exploratory windows cannot
support promotion without separate validation.

## Run Index

| Status | Configuration | Artifact |
| --- | --- | --- |
| Completed | `bddfe2d8` | [`20260723-123342Z__five-universes-three-windows__bddfe2d8`](../../artifacts/stock/backtests/components/selection-models/fundamental-technical-condition-count/20260723-123342Z__five-universes-three-windows__bddfe2d8/) |

## Results

Of 46,750 candidate/date rows, 14,026 (30.00%) had complete evidence and
received a condition count. Debt, margin, revenue, and EPS evidence were the
largest sources of incomplete rows.

| Count | 126-session return | vs SPY | vs universe | 252-session return | vs SPY | vs universe |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 12.11% | 1.26% | 1.27% | 22.35% | -1.14% | 0.20% |
| 1 | 7.27% | 0.14% | 0.26% | 13.96% | -4.66% | -2.39% |
| 2 | 5.19% | -0.69% | -0.43% | 10.34% | -4.81% | -3.15% |
| 3 | 4.46% | -1.24% | -1.23% | 10.59% | -3.48% | -2.21% |
| 4 | 3.69% | -1.31% | -1.36% | 11.30% | -2.02% | -0.96% |
| 5 | 3.46% | -1.45% | -1.62% | 12.00% | -1.06% | -0.13% |
| 6 | 4.68% | -0.10% | -0.11% | 11.82% | -1.11% | 0.13% |
| 7 | 7.48% | 1.45% | 1.74% | 13.89% | -0.10% | 1.34% |
| 8 | 3.56% | -2.37% | -2.64% | 9.04% | -1.79% | -1.74% |

At 126 sessions, Spearman correlation between count and excess return was
`-0.367` versus both benchmarks, with only two of eight adjacent transitions
improving. At 252 sessions, correlations were `0.567` versus SPY and `0.333`
versus the universe, but only four of eight SPY transitions and five of eight
universe transitions improved. The preregistered criterion required at least
five for both.

This diagnostic does not apply a
[portfolio policy](../../stages/OPERATIONS.md#portfolio-transitions-and-portfolio-policies)
or separate
[execution model](../../stages/OPERATIONS.md#execution-and-execution-models).

## Findings

Condition count is not an ordinal quality score in this sample. Outcomes
declined from zero through roughly five conditions, improved at seven, and
deteriorated again at eight. The strict conjunction therefore loses
information about condition identity and does not benefit reliably from simply
adding more passing conditions.

The dominant seven-condition signature omitted
`is_high_relative_volume`: it had 468 observations at 252 sessions, versus 38
for the strict eight-condition cohort. Its raw excess return versus SPY was
positive, while the strict cohort's was negative. This is a diagnostic clue,
not a causal comparison, because the cohorts differ by ticker and date.

The 30% complete-case coverage also means the result applies only to candidates
with all eight fields observed.

## Decision

Reject a generic count-threshold selector. Do not replace the strict
conjunction with an undifferentiated four-, six-, or seven-of-eight rule.

## Follow-up

Run a preregistered condition-identity ablation focused on abnormal relative
volume and the dominant seven-condition signature. Compare the same
ticker/date population with and without the volume requirement, and investigate
whether an up-volume spike is a poor immediate-entry signal rather than a
useful confirmation feature.
