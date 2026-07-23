# Fundamental Technical Momentum Seven Condition

Reusable [selection](../OPERATIONS.md#selection-and-selection-models) model.

## ID

`fundamental-technical-momentum-seven-condition`

## Stage Type

`selection-model`

## Purpose

Select stocks with improving fundamentals, reported institutional
accumulation, intact long-term trend, and benchmark-relative strength without
requiring an abnormal same-day up-volume event.

## Input Contract

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `as_of` | trading date or timestamp | Yes | Completed decision cutoff. |
| `candidates` | ordered instrument IDs | Yes | Point-in-time candidate population. |
| `features` | map of instrument ID to feature row | Yes | Evidence knowable at the cutoff. |
| `fallback_ticker` | ticker ID or `None` | No | Optional defensive target. |

Required booleans are EPS growth, margin improvement, revenue growth, debt
reduction, institutional accumulation, close above SMA200, and relative
strength above SPY. `is_high_relative_volume` is neither required nor treated
as false when missing. Ranking still requires `ret_252` and
`relative_volume_50`.

## Output Contract

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `as_of` | trading date or timestamp | Yes | Input cutoff echoed. |
| `eligibility` | map of instrument ID to decision/reasons | Yes | Per-condition exclusions. |
| `ranking` | ordered scored candidates | Yes | Deterministic eligible ranking. |
| `targets` | ordered ticker/weight pairs | Yes | Up to `target_count` equal-weight targets. |
| `fallback_used` | boolean | Yes | Whether fallback replaced an empty result. |

## Behavior

Require all seven declared booleans. Rank eligible candidates by descending
252-session return, descending 50-session relative volume, then instrument ID.
Emit up to `target_count` equal-weight targets. This descriptor removes only
the abnormal-volume eligibility gate; it does not reinterpret missing values
for the other conditions.

## Parameters

| name | type | required | default | constraints | description |
| --- | --- | --- | --- | --- | --- |
| `target_count` | positive integer | No | `10` | `>= 1`. | Maximum selected targets. |
| `fallback_mode` | enum | No | `empty` | `empty` or `fallback`. | Empty-result behavior. |
| `missing_data_policy` | enum | No | `exclude_and_report` | Fixed by descriptor. | Exclude unknown required evidence. |

## Data Requirements

Requires point-in-time quarterly fundamentals and institutional snapshots,
SMA200, 252-session stock and SPY returns, and 50 prior volume observations.

## Point-in-Time Rules

Use only evidence available by `as_of`. Filing dates govern fundamental and
institutional availability. Rolling features use completed rows only.

## Failure Behavior

Missing required evidence excludes only that candidate and is reported.
Invalid parameters fail before selection. Empty eligibility follows
`fallback_mode`.

## Benchmark Contract

Replay identical dated universes and compare with the strict eight-condition
model, SPY, dated equal-weight universe, and unfiltered momentum rank. Measure
coverage, top-selection forward returns, benchmark-relative returns, hit rate,
concentration, and stability across windows.

## Implementation

`stages/selection-models/fundamental_technical_momentum.py`

Public entry point: `select_without_high_relative_volume(...)`.
