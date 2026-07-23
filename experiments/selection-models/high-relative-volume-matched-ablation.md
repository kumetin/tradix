# High Relative Volume Matched Ablation

## Experiment ID

`high-relative-volume-matched-ablation`

## Status

`completed`

## Hypothesis

Within candidates satisfying the other seven conditions, abnormal up-volume
improves benchmark-relative forward outcomes.

## Reference Configuration

- [Selection model](../../stages/OPERATIONS.md#selection-and-selection-models):
  [`fundamental-technical-momentum`](../../stages/selection-models/fundamental-technical-momentum.md)
- Component protocol:
  [`high-relative-volume-matched-ablation`](../../backtests/components/selection-models/high-relative-volume-matched-ablation.md)
- [Evaluation plan](../../stages/OPERATIONS.md#evaluation-plans):
  [`fundamental-technical-momentum-exploratory`](../../configuration/evaluations/selection-models/fundamental-technical-momentum-exploratory.md)

## Declared Deltas

Use the immutable complete-evidence outcome tape from condition-count run
`bddfe2d8`. Require all seven non-volume conditions to be true. Within each
universe/date cell containing both groups, compare `is_high_relative_volume =
true` against `false`, equal-weighting securities inside each group.

## Success Criteria

At both 126 and 252 sessions, the mean paired return difference must be
positive, at least 55% of matched cells must favor the volume-positive group,
and the deterministic date-cell bootstrap 95% lower bound must not be
negative. Direction should be positive in at least three of the five universes
and two of the three windows. At least 20 treated observations are required.

## Run Index

| Status | Configuration | Artifact |
| --- | --- | --- |
| Completed, underpowered | `80a62dc9` | [`20260723-123910Z__matched-seven-condition-base__80a62dc9`](../../artifacts/stock/backtests/components/selection-models/high-relative-volume-matched-ablation/20260723-123910Z__matched-seven-condition-base__80a62dc9/) |

## Results

Only 13 universe/date cells and 14 treated observations were matched at each
horizon. Mean paired differences were `+0.10%` at 126 sessions and `+4.62%` at
252 sessions, but only 38.46% and 53.85% of cells favored treatment. Bootstrap
95% intervals were `[-11.24%, +11.46%]` and `[-7.45%, +18.02%]`.

This diagnostic does not apply a
[portfolio policy](../../stages/OPERATIONS.md#portfolio-transitions-and-portfolio-policies)
or separate
[execution model](../../stages/OPERATIONS.md#execution-and-execution-models).

## Findings

The exact per-50-stock-universe design is too sparse to distinguish a volume
effect. It failed the minimum sample requirement and every horizon's bootstrap
interval crossed zero.

## Decision

Inconclusive; do not use this run to retain or remove the condition.

## Follow-up

Use the preregistered combined-universe replication, which preserves same-date
matching while pooling the five disjoint random universe samples.
