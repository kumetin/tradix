# Classic 12-1 Momentum SPY SMA200 Gated

## ID

`classic-12-1-momentum-spy-sma200-gated`

## Stage Type

`selection-model`

## Purpose

Rank a point-in-time equity universe by classic 12-1 momentum only when the
broad U.S. market is in a positive long-term trend. Emit cash intent when SPY
closes below its 200-session simple moving average.

## Input Contract

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `as_of` | completed trading date | Yes | Decision cutoff. |
| `candidates` | ordered instrument IDs | Yes | Point-in-time equity population. |
| `features` | map of instrument ID to feature row | Yes | `ret_252_21` values knowable at cutoff. |
| `market_features` | feature row | Yes | Completed SPY adjusted close and SMA200 at cutoff. |
| `fallback_ticker` | ticker ID or `None` | No | Unused; defensive state is cash. |

## Output Contract

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `as_of` | completed trading date | Yes | Input cutoff echoed. |
| `eligibility` | map of instrument ID to decision/reasons | Yes | Market-gate and data decisions. |
| `ranking` | ordered scored candidates | Yes | Classic 12-1 ranking when gate is open; empty otherwise. |
| `targets` | ordered ticker/weight pairs | Yes | Equal-weight top-ten intent or empty cash intent. |
| `fallback_used` | boolean | Yes | Always false; cash is normal gate behavior. |

## Behavior

At the completed decision cutoff:

1. Require finite positive SPY adjusted close and SMA200.
2. If SPY adjusted close is below SMA200, emit no targets.
3. Otherwise apply the exact eligibility, descending `ret_252_21` ranking,
   deterministic tie-break, top-ten count, and equal weights defined by
   [Classic 12-1 Momentum](classic-12-1-momentum.md).

Equality opens the gate. The gate is evaluated only at the monthly decision
cycle; it is not a daily stop.

## Parameters

| name | type | required | default | constraints | description |
| --- | --- | --- | --- | --- | --- |
| `target_count` | positive integer | No | `10` | Fixed by descriptor. | Equal-weight equity targets when the gate is open. |
| `lookback_sessions` | integer | No | `252` | Fixed by descriptor. | Start of the stock momentum interval. |
| `skip_sessions` | integer | No | `21` | Fixed by descriptor. | Recent stock sessions omitted from momentum. |
| `market_sma_sessions` | integer | No | `200` | Fixed by descriptor. | SPY trend window. |
| `closed_gate_target` | enum | No | `cash` | Fixed by descriptor. | Portfolio intent below the market SMA. |

## Data Requirements

Requires point-in-time membership; at least 253 valid adjusted closes per
candidate; at least 200 valid SPY adjusted closes; a completed SPY close and
SMA200 at each cutoff; and split/dividend-adjusted stock prices.

## Point-in-Time Rules

Candidate momentum and the SPY gate use only completed observations at or
before `as_of`. Orders cannot execute before the next session. Future
membership, prices, moving averages, and delisting outcomes are prohibited.

## Failure Behavior

Fail the decision cycle when SPY close or SMA200 is unavailable. Exclude and
report candidates with invalid momentum history. An open gate with no eligible
candidates emits empty targets and reports the data failure. A closed gate
emits empty targets as intended cash exposure, not as fallback.

## Benchmark Contract

Replay identical dated universes and compare with ungated classic 12-1,
SPY, VFMO, and the dated equal-weight eligible universe. Report gate-open
frequency, return, drawdown, time underwater, turnover, rolling 12-month
excess return, calendar-year and ticker concentration, costs, and coverage.
The gate adds value only if drawdown improves without eliminating
benchmark-relative return.

## Implementation

`scripts/backtests/strategies/classic_12_1_momentum_rotation.py`

Public configuration: `--market-sma-window 200`.
