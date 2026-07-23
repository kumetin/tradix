# Fundamental Technical Momentum Exploratory Benchmark

## Experiment ID

`fundamental-technical-momentum-exploratory`

## Status

`rejected_for_promotion`

## Hypothesis

The full conjunction produces higher benchmark-relative forward returns than
unfiltered, fundamental-only, technical/demand-only, and leave-one-condition-out
candidate selection across multiple exploratory regimes.

## Reference Configuration

- [Selection model](../../stages/OPERATIONS.md#selection-and-selection-models):
  [`fundamental-technical-momentum`](../../stages/selection-models/fundamental-technical-momentum.md)
- [Component protocol](../../backtests/components/selection-models/fundamental-technical-momentum.md)
- [Evaluation plan](../../stages/OPERATIONS.md#evaluation-plans):
  [`fundamental-technical-momentum-exploratory`](../../configuration/evaluations/selection-models/fundamental-technical-momentum-exploratory.md)

## Declared Deltas

- Universes: the five pre-existing random current-S&P-500 50-stock universes.
- Variants: full conjunction, unfiltered, fundamental-only,
  technical/demand-only, and all eight leave-one-condition-out variants.
- Target counts: `1`, `5`, `10`, and `20`.
- Horizons: `21`, `63`, `126`, `252`, and `378` valid sessions.

## Success Criteria

The full model must have nonzero usable coverage and show positive mean excess
return versus both SPY and the dated equal-weight candidate universe in a
majority of universe/window cells at both 126 and 252 sessions. Evidence must
not be concentrated in one universe, ticker, or window. No promotion decision
may be made from these current-constituent development partitions.

## Run Index

| Status | Configuration | Artifact |
| --- | --- | --- |
| Interrupted before output | `19604262` | `20260723-105707Z__exploratory-five-universes__19604262` |
| Completed | `19604262` | [`20260723-105953Z__exploratory-five-universes__19604262`](../../artifacts/stock/backtests/components/selection-models/fundamental-technical-momentum/20260723-105953Z__exploratory-five-universes__19604262/) |

## Results

The full conjunction and technical/demand baseline produced zero observations
at every horizon because institutional-accumulation evidence was unavailable
at every historical cutoff.

For target count 10, the leave-institutional-out ablation produced 104
observations through 252 sessions. Mean excess returns versus SPY were
`-0.63%`, `-3.21%`, `-2.61%`, and `-5.18%` at 21, 63, 126, and 252 sessions.
Mean excess returns versus the equal-weight universe were `-0.24%`, `-3.53%`,
`-2.32%`, and `-3.82%`. At 378 sessions, 103 observations averaged `-8.71%`
versus SPY and `-8.53%` versus the universe.

The fundamental-only baseline also lagged both benchmarks at every horizon.
The unfiltered rank baseline outperformed both, but that result is descriptive
and subject to current-universe bias.

This component experiment does not apply an
[execution model](../../stages/OPERATIONS.md#execution-and-execution-models).

## Findings

The experiment cannot evaluate the full model's predictive value because
point-in-time institutional coverage does not overlap the price tape.
Converting the missing field to false or backfilling the current snapshot would
violate the component's missing-data and point-in-time rules.

Dropping only institutional accumulation makes the conjunction measurable but
does not improve benchmark-relative outcomes in this exploratory sample.

## Decision

Do not promote the full model or its leave-institutional-out ablation. Treat
the completed run as a data-coverage diagnosis and negative exploratory
evidence, not as a clean falsification of the full eight-condition hypothesis.

## Follow-up

Acquire historically available institutional snapshots with genuine
publication dates, regenerate daily features, and preregister a new validation
experiment before rerunning the full conjunction.
