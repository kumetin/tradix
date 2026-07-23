# Partial Profit Breakeven Time Exit Baseline

## Experiment ID

`partial-profit-breakeven-time-exit-baseline`

## Status

`rejected_for_promotion`

## Hypothesis

The complete policy improves mean return and adverse-tail behavior relative to
full holding and simpler exit variants without excessive turnover.

## Reference Configuration

- [Portfolio policy](../../stages/OPERATIONS.md#portfolio-transitions-and-portfolio-policies):
  [`partial-profit-breakeven-time-exit`](../../stages/portfolio-policies/partial-profit-breakeven-time-exit.md)
- Component protocol:
  [`partial-profit-breakeven-time-exit`](../../backtests/components/portfolio-policies/partial-profit-breakeven-time-exit.md)
- [Evaluation plan](../../stages/OPERATIONS.md#evaluation-plans):
  [`fundamental-technical-momentum-exploratory`](../../configuration/evaluations/selection-models/fundamental-technical-momentum-exploratory.md)

## Declared Deltas

Use target-count-10 entry tapes from the completed SEC-13F-backed selector
benchmark for the full, unfiltered, fundamental-only, and technical/demand-only
sources. Compare the five exit variants declared by the component protocol.

## Success Criteria

Relative to full holding, the complete policy must improve either mean return
without worsening the 5th-percentile return, or improve the 5th-percentile
return by at least 2 percentage points without reducing mean return by more
than 1 percentage point. The result should be directionally consistent across
at least three of four entry sources. Quantity/cash conservation error must be
zero within floating-point tolerance.

## Run Index

| Status | Configuration | Artifact |
| --- | --- | --- |
| Invalid unequal-cohort pass | `36594b8b` | [`20260723-121345Z__selector-entry-tapes__36594b8b`](../../artifacts/stock/backtests/components/portfolio-policies/partial-profit-breakeven-time-exit/20260723-121345Z__selector-entry-tapes__36594b8b/) |
| Completed paired-cohort run | `7180ea58` | [`20260723-121552Z__selector-entry-tapes__7180ea58`](../../artifacts/stock/backtests/components/portfolio-policies/partial-profit-breakeven-time-exit/20260723-121552Z__selector-entry-tapes__7180ea58/) |

The first pass allowed early-exit variants to retain late entries lacking the
full-hold policy's 379-session exit reference. It is preserved for audit but
must not be used for variant comparisons. The replacement run requires common
history before invoking any variant.

## Results

The paired run evaluated 12,663 entries through all five variants. Relative to
full holding, the complete policy produced:

| Entry source | Trades | Full-hold mean | Policy mean | Mean delta | Full-hold P05 | Policy P05 | P05 delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Full conjunction | 38 | 13.03% | 0.40% | -12.63% | -25.48% | -7.50% | +17.98% |
| Fundamental only | 3,083 | 20.02% | 0.84% | -19.19% | -36.23% | -7.51% | +28.72% |
| Technical/demand only | 342 | 22.09% | 2.38% | -19.70% | -34.74% | -7.50% | +27.24% |
| Unfiltered | 9,200 | 29.69% | 3.18% | -26.51% | -32.61% | -7.54% | +25.07% |

The complete policy's mean holding period was 50–70 sessions. Its stagnation
exit was the final exit for 53% of unfiltered entries, 55% of fundamental-only
entries, 62% of technical/demand entries, and 79% of the small full-conjunction
sample. Maximum cash-conservation error was below `1e-12`, and quantity error
was zero.

This isolated component benchmark references market bars after entry only to
score policy outcomes and does not apply a separate
[execution model](../../stages/OPERATIONS.md#execution-and-execution-models).

## Findings

The policy is effective at bounding trade-level downside but pays for that
protection by truncating the positive skew that drives long-horizon equity
returns. It failed the preregistered trade-off criterion in every entry source:
the P05 improvement was large, but mean return fell by much more than the
permitted one percentage point.

The partial-profit variant without the stagnation exit retained more mean
return than the complete policy in the three adequately sized entry sources,
but still substantially lagged full holding. A fixed 7.5% stop preserved more
mean return than either partial-profit variant on the unfiltered and
technical/demand tapes, at the cost of a moderately worse P05.

The 38-trade full-conjunction result is too small to override the broader
evidence.

## Decision

Do not promote the complete policy as the default portfolio policy. It may be
appropriate only for an explicitly tail-risk-first mandate that accepts a
large reduction in expected return.

## Follow-up

If further policy research is desired, preregister a component experiment that
isolates the stagnation rule from the stop and partial-profit rules. Compare
longer stagnation windows or a trend-aware opportunity-cost exit without
reusing this exploratory result as a clean holdout.
