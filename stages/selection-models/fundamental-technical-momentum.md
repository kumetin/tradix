# Fundamental Technical Momentum

## ID

`fundamental-technical-momentum`

## Stage Type

`selection-model`

## Purpose

Provide [selection](../OPERATIONS.md#selection-and-selection-models) of stocks
showing simultaneous point-in-time fundamental improvement,
institutional demand, abnormal up-day volume, long-term trend health, and
benchmark-relative momentum.

## Input Contract

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `as_of` | trading date or timestamp | Yes | Completed decision cutoff. |
| `candidates` | ordered instrument IDs | Yes | Point-in-time candidate population. |
| `features` | map of instrument ID to feature row | Yes | Latest feature row knowable at `as_of`. |
| `fallback_ticker` | ticker ID or `None` | No | Optional defensive target. |

Each feature row requires `is_eps_growing`,
`is_profit_margins_increasing`, `is_revenue_rises`, `is_debt_lowers`,
`is_institutional_accumalation_rising`, `is_high_relative_volume`,
`is_above_moving_average`, `is_relative_strength_high`, `ret_252`, and
`relative_volume_50`.

## Output Contract

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `as_of` | trading date or timestamp | Yes | Input cutoff echoed. |
| `eligibility` | map of instrument ID to decision/reasons | Yes | Per-condition results and exclusions. |
| `ranking` | ordered scored candidates | Yes | Eligible candidates ordered deterministically. |
| `targets` | ordered ticker/weight pairs | Yes | Up to `target_count` equal-weight targets. |
| `fallback_used` | boolean | Yes | Whether the configured fallback replaced an empty result. |

## Behavior

A candidate is eligible only when every required boolean feature is `true`.
This intentionally tests the proposal's conjunction without converting unknown
evidence to false evidence or compensating for a failed condition with a high
score elsewhere.

Rank eligible candidates by descending `ret_252`, then descending
`relative_volume_50`, then ascending instrument ID. Select the first
`target_count` and assign equal weights. If no candidate qualifies, use the
configured fallback only when `fallback_mode=fallback`; otherwise emit no
targets.

## Parameters

| name | type | required | default | constraints | description |
| --- | --- | --- | --- | --- | --- |
| `target_count` | positive integer | No | `10` | `>= 1`. | Maximum number of equal-weight targets. |
| `fallback_mode` | enum | No | `empty` | `empty` or `fallback`. | Empty-result behavior. |
| `missing_data_policy` | enum | No | `exclude_and_report` | Fixed by descriptor. | Excludes unknown evidence without treating it as a failed observation. |

## Data Requirements

Requires comparable quarterly fundamentals with publication-based
`available_date`, dated institutional snapshots, 252 valid adjusted-close
observations for relative strength and SMA200, and 50 prior valid volume rows.
Missing price or volume rows are not forward-filled.

## Point-in-Time Rules

Fundamentals and ownership observations are usable only from their
`available_date`, never their fiscal period end. The current decision row and
all rolling inputs must be complete by `as_of`. Restatements filed later must
not rewrite earlier decisions. Benchmark returns must use the same cutoff.

## Failure Behavior

Missing or malformed required booleans make only that candidate ineligible and
produce `missing:<field>`. Missing numeric ranking values exclude the candidate
with an explicit reason. Invalid parameters fail before selection. An empty
eligible set follows `fallback_mode`.

## Benchmark Contract

Replay identical dated fixtures and compare the conjunction against:

- the dated equal-weight candidate universe;
- SPY;
- technical-only (`is_above_moving_average` and relative strength);
- fundamental-only (EPS, margin, revenue, and debt); and
- leave-one-condition-out variants.

Measure top-selection forward excess return and hit rate at 21, 63, 126, and
252 sessions, rank-bucket monotonicity, coverage/fallback rate, turnover, and
stability across market regimes. Promotion requires a locked holdout and must
not assume a 60%–70% win rate or any particular expectancy.

## Implementation

`stages/selection-models/fundamental_technical_momentum.py`

Public entry point: `select(...)`.
