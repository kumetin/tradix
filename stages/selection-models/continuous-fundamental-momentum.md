# Continuous Fundamental Momentum

Reusable [selection](../OPERATIONS.md#selection-and-selection-models) model.

## ID

`continuous-fundamental-momentum`

## Stage Type

`selection-model`

## Purpose

Rank stocks by both trailing momentum and the strength of point-in-time
fundamental and institutional evidence without using those signals as hard
pass/fail gates.

## Input Contract

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `as_of` | trading date or timestamp | Yes | Completed decision cutoff. |
| `candidates` | ordered instrument IDs | Yes | Point-in-time candidate population. |
| `features` | map of instrument ID to feature row | Yes | Evidence knowable at the cutoff. |
| `fallback_ticker` | ticker ID or `None` | No | Optional defensive target. |

The five scored evidence fields are EPS growth, margin improvement, revenue
growth, debt reduction, and institutional accumulation. Momentum is the
252-session adjusted-close return.

## Output Contract

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `as_of` | trading date or timestamp | Yes | Input cutoff echoed. |
| `eligibility` | map of instrument ID to decision/reasons | Yes | Data-sufficiency decisions. |
| `ranking` | ordered scored candidates | Yes | Composite score and its components. |
| `targets` | ordered ticker/weight pairs | Yes | Up to `target_count` equal-weight targets. |
| `fallback_used` | boolean | Yes | Whether fallback replaced an empty result. |

## Behavior

Require `ret_252` and at least four known evidence fields. For each eligible
candidate, compute `fundamental_score` as true observations divided by known
observations. Compute `momentum_percentile` from ascending `ret_252` rank among
eligible candidates, using `1.0` for a singleton. The composite score is
`0.5 * momentum_percentile + 0.5 * fundamental_score`. Rank by descending
composite score, descending `ret_252`, then instrument ID, and emit
equal-weight targets.

Technical trend, benchmark-relative strength, and abnormal volume are not
eligibility gates because they duplicate or condition the momentum signal
being ranked.

## Parameters

| name | type | required | default | constraints | description |
| --- | --- | --- | --- | --- | --- |
| `target_count` | positive integer | No | `10` | `>= 1`. | Maximum selected targets. |
| `fallback_mode` | enum | No | `empty` | `empty` or `fallback`. | Empty-result behavior. |
| `minimum_known_fundamentals` | integer | No | `4` | Fixed by descriptor; `4` of `5`. | Evidence sufficiency floor. |
| `momentum_weight` | decimal | No | `0.5` | Fixed by descriptor. | Momentum-percentile weight. |
| `fundamental_weight` | decimal | No | `0.5` | Fixed by descriptor. | Fundamental-score weight. |

## Data Requirements

Requires 252 valid adjusted-close sessions and point-in-time quarterly
fundamental and institutional snapshots for at least four of the five scored
fields.

## Point-in-Time Rules

Use only evidence available by `as_of`. Filing dates govern fundamental and
institutional availability. The trailing return ends at the completed cutoff;
future bars are never passed to selection.

## Failure Behavior

Missing `ret_252` or more than one unknown evidence field excludes the
candidate and records the reason. Invalid parameters fail before selection.
Empty eligibility follows `fallback_mode`.

## Benchmark Contract

Replay identical dated universes and compare top selections with momentum-only
ranking and the frozen seven-condition selector. Measure coverage, forward
returns, benchmark-relative outcomes, hit rate, concentration, and
cross-universe consistency.

## Implementation

`stages/selection-models/continuous_fundamental_momentum.py`

Public entry point: `select(...)`.
