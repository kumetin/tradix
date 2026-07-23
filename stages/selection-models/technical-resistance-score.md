# Technical Resistance Score

## ID

`technical-resistance-score`

## Stage Type

`selection-model`

## Purpose

Provide reusable [selection](../OPERATIONS.md#selection-and-selection-models)
of one equity whose point-in-time trend, market-relative strength,
controlled pullback, and resistance reward geometry produce the highest
technical score.

## Input Contract

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `as_of` | trading date or timestamp | Yes | Decision cutoff. |
| `candidates` | ordered instrument records | Yes | Point-in-time equity universe. |
| `features` | map of instrument ID to feature history | Yes | Adjusted OHLCV, moving averages, returns, RSI, and volume rows no later than `as_of`. |
| `benchmark_features` | feature history | Yes | Point-in-time SPY return history over identical sessions. |

## Output Contract

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `as_of` | trading date or timestamp | Yes | Input cutoff echoed for traceability. |
| `eligibility` | map of instrument ID to decision/reasons | Yes | Warm-up, required-field, support, and resistance decisions. |
| `ranking` | ordered scored candidate records | Yes | Total and component scores, support, resistance, reward/risk, and reason codes. |
| `targets` | one-element ordered target record or empty | Yes | Selected instrument, weight `1.0`, score, support, and resistance target. |
| `fallback_used` | boolean | Yes | Always `false`; the descriptor has no fallback asset. |

## Behavior

Require valid actual rows and non-null inputs for every configured lookback.
Construct support as the highest value no greater than `1.03 × adjusted_close`
among SMA20, SMA50, SMA150, and the lowest adjusted low over 63 sessions.
Construct resistance as the highest adjusted high over 126 sessions.

Calculate the `0–70` score:

1. Trend, maximum 20: add 5 for each of price above SMA150, SMA150 above its
   value 21 sessions earlier, price above SMA50, and SMA50 above SMA150.
2. Relative strength, maximum 20: add 4 for each of 63-, 126-, and 252-session
   return exceeding SPY; add `8 ×` the percentile rank of 126-session excess
   return across eligible candidates.
3. Pullback quality, maximum 15: add 5 for each of price within 5% of support,
   RSI(14) in `[40, 60]`, and latest-20-session mean volume below the preceding
   20-session mean.
4. Reward geometry, maximum 15: add 5 when price is within 6% of support; add
   10, 7, 3, or 0 when `(resistance - price) / (price - support)` is
   respectively `>=3`, `>=2`, `>=1`, or `<1`.

Rank total score descending and break ties by ascending stable instrument ID.
Emit the first candidate at weight `1.0`. Return an empty target set when none
is eligible.

## Parameters

| name | type | required | default | constraints | description |
| --- | --- | --- | --- | --- | --- |
| `target_count` | positive integer | No | `1` | Fixed by descriptor. | Number of selected targets. |
| `support_low_window` | positive trading-day count | No | `63` | Fixed by descriptor. | Recent-low support lookback. |
| `resistance_window` | positive trading-day count | No | `126` | Fixed by descriptor. | Trailing adjusted-high target lookback. |
| `relative_return_windows` | list of positive trading-day counts | No | `63,126,252` | Fixed by descriptor. | Stock-versus-SPY comparison windows. |
| `relative_percentile_window` | positive trading-day count | No | `126` | Fixed by descriptor. | Excess-return field ranked cross-sectionally. |
| `rsi_window` | positive trading-day count | No | `14` | Fixed by descriptor. | RSI window. |
| `volume_window` | positive trading-day count | No | `20` | Fixed by descriptor. | Recent and preceding volume windows. |
| `missing_data_policy` | enum | No | `exclude_and_report` | Fixed by descriptor. | Excludes incomplete candidates rather than imputing. |
| `tie_breaker` | field name | No | `instrument_id` | Fixed by descriptor; unique and ascending. | Makes top-one selection deterministic. |

## Data Requirements

At least 253 valid daily rows are required for each candidate and SPY. Required
fields are adjusted open, high, low, close, volume, SMA20, SMA50, SMA150,
RSI(14), and 63-, 126-, and 252-session adjusted returns. Missing OHLCV rows
are skipped, never forward-filled.

## Point-in-Time Rules

Rows, benchmark values, universe membership, and derived features must be
effective and knowable by `as_of`. Cross-sectional percentiles use only the
dated candidate set. Future highs, later membership, and revised future
fundamentals are prohibited.

## Failure Behavior

Exclude and report candidates with insufficient history, missing required
fields, invalid support, nonpositive price-to-support risk, or invalid
resistance. Return empty targets if none qualify. Do not relax predicates or
substitute SPY as a portfolio target.

## Benchmark Contract

Replay identical dated candidate/feature fixtures. Measure deterministic score
and rank reproduction, score-bucket monotonicity, top-selection excess return,
target reachability, first-hit time, adverse excursion, missing-data exclusion,
and performance versus random, equal-weight, and simple momentum selectors.

## Implementation

`scripts/backtests/strategies/technical_resistance_runner.py`

Public selection entry point: `select_winner(...)`.
