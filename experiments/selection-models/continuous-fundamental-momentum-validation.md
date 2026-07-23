# Continuous Fundamental Momentum Validation

## Experiment ID

`continuous-fundamental-momentum-validation`

## Status

`rejected_for_promotion`

## Hypothesis

Using point-in-time fundamental conditions as a continuous ranking contribution
will improve top-selection forward outcomes over momentum-only ranking without
the sparse coverage and concentration of hard conjunction filters.

## Reference Configuration

- [Selection model](../../stages/OPERATIONS.md#selection-and-selection-models):
  [`continuous-fundamental-momentum`](../../stages/selection-models/continuous-fundamental-momentum.md)
- Component protocol:
  [`continuous-fundamental-momentum-validation`](../../backtests/components/selection-models/continuous-fundamental-momentum-validation.md)
- [Evaluation plan](../../stages/OPERATIONS.md#evaluation-plans):
  [`continuous-fundamental-momentum-validation`](../../configuration/evaluations/selection-models/continuous-fundamental-momentum-validation.md)

## Declared Deltas

Replace hard fundamental and technical eligibility gates with a frozen 50/50
composite of 252-session momentum percentile and the proportion of five known
fundamental/sponsorship conditions satisfied. Require four known conditions.
Compare target counts 5, 10, and 20 across the five existing random universes.

## Success Criteria

At target count 10, the continuous model must produce at least 500 forward
observations per primary horizon and positive mean excess return versus SPY and
the dated equal-weight universe at both 63 and 126 sessions. It must also beat
momentum-only mean return at both horizons, with positive paired
decision-date differences in at least three of five universes. No single ticker
may contribute more than 15% of observations.

## Run Index

| Status | Configuration | Artifact |
| --- | --- | --- |
| Completed | `1adb0fee` | [`20260723-125803Z__unused-2025h2__1adb0fee`](../../artifacts/stock/backtests/components/selection-models/continuous-fundamental-momentum-validation/20260723-125803Z__unused-2025h2__1adb0fee/) |

## Results

At target count 10, all full-coverage variants produced 1,300 observations:

| Variant | Horizon | Mean return | Excess vs SPY | Excess vs universe |
| --- | ---: | ---: | ---: | ---: |
| Continuous | 21 | 2.23% | 0.70% | 0.50% |
| Momentum only | 21 | 3.85% | 2.32% | 2.12% |
| Continuous | 63 | 6.02% | 3.71% | 1.95% |
| Momentum only | 63 | 9.12% | 6.82% | 5.05% |
| Continuous | 126 | 13.58% | 6.41% | 4.16% |
| Momentum only | 126 | 21.92% | 14.75% | 12.49% |

The continuous model satisfied observation count, benchmark-relative return,
and concentration requirements, but underperformed momentum-only ranking by
3.10 percentage points at 63 sessions and 8.34 points at 126 sessions.
Its paired universe difference was positive in only one of five universes at
63 sessions and zero of five at 126 sessions.

The seven-condition comparator generated only 163 observations. Its aggregate
returns were higher, but one ticker supplied 15.95% of observations and the
selector remained sparse; this run was not preregistered to promote that
previously rejected model.

## Findings

The fundamental evidence contribution consistently displaced stronger
momentum names without compensating forward return. Positive absolute and
benchmark-relative performance therefore does not establish incremental model
value: the simpler momentum-only comparator was materially better in every
aggregate horizon and almost every universe.

The 2025-07-21 through 2026-01-16 decision window is now inspected and cannot
be reused as a clean test for score-weight or evidence-rule changes.

## Decision

Do not promote the continuous 50/50 selector. It failed both primary
incremental-performance criteria.

## Follow-up

Use momentum-only ranking as the selection baseline for any portfolio-policy
or full-strategy harness. Do not tune another fundamental composite on the
consumed windows. A future fundamental model should first demonstrate
incremental rank information in development data and reserve a new untouched
period before promotion.
