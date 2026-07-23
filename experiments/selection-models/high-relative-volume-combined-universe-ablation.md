# High Relative Volume Combined-Universe Ablation

## Experiment ID

`high-relative-volume-combined-universe-ablation`

## Status

`rejected_for_promotion`

## Hypothesis

Within the combined 250-stock population satisfying the other seven
conditions, abnormal up-volume improves forward outcomes.

## Reference Configuration

- [Selection model](../../stages/OPERATIONS.md#selection-and-selection-models):
  [`fundamental-technical-momentum`](../../stages/selection-models/fundamental-technical-momentum.md)
- Component protocol:
  [`high-relative-volume-matched-ablation`](../../backtests/components/selection-models/high-relative-volume-matched-ablation.md)
- [Evaluation plan](../../stages/OPERATIONS.md#evaluation-plans):
  [`fundamental-technical-momentum-exploratory`](../../configuration/evaluations/selection-models/fundamental-technical-momentum-exploratory.md)

## Declared Deltas

Relative to the exact per-50-stock-universe match, combine the five disjoint
random universes into one 250-stock research population. Continue matching on
the identical window, cutoff, and horizon, and continue requiring all seven
non-volume conditions in both groups.

## Success Criteria

At both 126 and 252 sessions, mean paired return difference must be positive,
at least 55% of matched dates must favor the volume-positive group, and the
date-cell bootstrap 95% lower bound must not be negative. Direction must be
positive in at least two of three windows, with at least 30 treated
observations.

## Run Index

| Status | Configuration | Artifact |
| --- | --- | --- |
| Completed | `637b2472` | [`20260723-124023Z__matched-seven-condition-base__637b2472`](../../artifacts/stock/backtests/components/selection-models/high-relative-volume-matched-ablation/20260723-124023Z__matched-seven-condition-base__637b2472/) |

## Results

The combined-universe match retained 31 treated observations and 74 controls
across 24 matched dates at each horizon.

| Horizon | Treated | Control | Paired difference | Dates favoring volume | Bootstrap 95% |
| ---: | ---: | ---: | ---: | ---: | --- |
| 21 | -0.59% | 0.05% | -0.64% | 50.00% | [-3.31%, 2.00%] |
| 63 | -0.46% | 2.62% | -3.08% | 50.00% | [-10.37%, 3.59%] |
| 126 | 2.57% | 10.07% | -7.51% | 45.83% | [-19.96%, 2.80%] |
| 252 | 6.09% | 10.65% | -4.57% | 45.83% | [-15.71%, 6.55%] |
| 378 | 9.51% | 19.72% | -10.21% | 37.50% | [-23.30%, 3.40%] |

The effect was negative in the 2021–2022 and 2023–2024H1 windows at both
primary horizons. The recent window was positive but contained only three
matched dates.

This diagnostic does not apply a
[portfolio policy](../../stages/OPERATIONS.md#portfolio-transitions-and-portfolio-policies)
or separate
[execution model](../../stages/OPERATIONS.md#execution-and-execution-models).

## Findings

The abnormal up-volume condition did not improve immediate-entry outcomes
within the seven-condition base. Point estimates were negative at every
horizon, including materially negative differences at 126 and 252 sessions.
Bootstrap intervals remained wide and crossed zero, so the experiment does not
prove a harmful causal effect, but it clearly fails to support the condition.

The recent positive subgroup is too small to establish a regime interaction.

## Decision

Do not retain `is_high_relative_volume` as a required conjunction condition on
the strength of the current evidence. The preregistered success criteria failed
at both primary horizons.

## Follow-up

Define a new selector variant that keeps the other seven conditions but removes
abnormal up-volume from eligibility. Benchmark it as a distinct model on a
separately declared validation plan. A later experiment may test volume as a
delayed-entry or exhaustion signal rather than immediate confirmation.
