# Technical Resistance Score SPY SMA200 Gated

## ID

`technical-resistance-score-spy-sma200-gated`

## Stage Type

`selection-model`

## Purpose

Provide gated
[selection](../OPERATIONS.md#selection-and-selection-models) of the top
[Technical Resistance Score](technical-resistance-score.md) candidate only
when the point-in-time SPY regime permits new equity risk.

## Input Contract

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `as_of` | trading date or timestamp | Yes | Decision cutoff. |
| `candidates` | ordered instrument records | Yes | Point-in-time equity universe. |
| `features` | map of instrument ID to feature history | Yes | Candidate features through `as_of`. |
| `benchmark_features` | point-in-time SPY feature history | Yes | SPY adjusted close, SMA200, and relative-return inputs through `as_of`. |

## Output Contract

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `as_of` | trading date or timestamp | Yes | Input cutoff echoed. |
| `eligibility` | map of instrument ID to decision/reasons | Yes | Base eligibility plus market-regime reason. |
| `ranking` | ordered scored candidates | Yes | Base technical ranking when the regime gate is open. |
| `targets` | one target or empty | Yes | Top weight-1.0 target when SPY is at or above SMA200; otherwise empty. |
| `fallback_used` | boolean | Yes | Always `false`. |

## Behavior

At the completed decision close, require
`SPY adjusted_close >= SPY sma_200`. If false, emit an empty target set with
reason `spy_below_sma200`; do not rank or enter a replacement defensive asset.
If true, apply every eligibility, score, ranking, and tie-breaking rule from
[Technical Resistance Score](technical-resistance-score.md) unchanged and emit
its top target.

## Parameters

| name | type | required | default | constraints | description |
| --- | --- | --- | --- | --- | --- |
| `market_benchmark` | instrument ID | No | `SPY` | Fixed by descriptor. | Regime benchmark. |
| `market_sma_window` | positive trading-day count | No | `200` | Fixed by descriptor. | Long-term regime average. |
| `market_gate_operator` | enum | No | `close_at_or_above` | Fixed by descriptor; `>=`. | Opens the selection gate. |
| `target_count` | positive integer | No | `1` | Fixed by descriptor. | Maximum selected targets. |
| `base_selection_model` | descriptor ID | No | `technical-resistance-score` | Fixed by descriptor. | Ranking invoked when the gate is open. |
| `missing_data_policy` | enum | No | `empty_and_report` | Fixed by descriptor. | Missing SPY state closes the gate. |

## Data Requirements

Requires all base-selector data plus at least 200 actual SPY observations for
SMA200. Missing rows are not forward-filled.

## Point-in-Time Rules

The SPY close and SMA200 must be known at the monthly decision cutoff and use
no later observations. The gate affects only new targets; it does not force an
existing holding to exit.

## Failure Behavior

Missing SPY close or SMA200 produces an empty target set and explicit reason.
Base-[selection](../OPERATIONS.md#selection-and-selection-models) failures retain their original exclusions and empty-target
behavior.

## Benchmark Contract

Replay identical dated feature fixtures and compare target availability,
turnover, cash drag, drawdown, and forward outcomes against the ungated base
selector, SMA150 gating, and always-empty controls.

## Implementation

`scripts/backtests/strategies/technical_resistance_runner.py`

The `run(...)` event loop applies this descriptor with
`market_regime_sma_window=200` before calling `select_winner(...)`.
