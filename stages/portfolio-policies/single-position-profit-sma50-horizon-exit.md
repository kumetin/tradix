# Single Position Profit SMA50 Horizon Exit

## ID

`single-position-profit-sma50-horizon-exit`

## Stage Type

`portfolio-policy`

## Purpose

Own the [portfolio transition](../OPERATIONS.md#portfolio-transitions-and-portfolio-policies)
for one selected position at a time, sell the full position at a fixed profit
target, invalidate an open holding after a completed daily close below that
day's SMA50, and enforce a maximum trading-session horizon.

## Input Contract

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `as_of` | trading date or timestamp | Yes | Transition decision time and knowledge cutoff. |
| `selection_intent` | zero or one target record | Yes | Upstream [selection](../OPERATIONS.md#selection-and-selection-models) instrument and weight. |
| `portfolio_state` | positions and lots | Yes | Filled quantity, entry price/session, open orders, and pending SMA50 signal. |
| `cash_state` | settled and unsettled ledger | Yes | Cash available for entry. |
| `daily_market_state` | completed adjusted daily feature row | Conditional | Current adjusted close and same-session SMA50 while a position is active. |
| `session_index` | exchange-session index | Yes | Counts actual trading sessions from entry. |

## Output Contract

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `as_of` | trading date or timestamp | Yes | Input time echoed for traceability. |
| `orders` | ordered order intents | Yes | Entry, profit limit, next-open SMA50 liquidation, horizon liquidation, or no-op. |
| `retained_positions` | instrument IDs with reasons | Yes | Positions retained because no exit condition is known at `as_of`. |
| `unallocated_cash` | amount with reason | Yes | Cash waiting while flat or after liquidation. |
| `constraint_events` | ordered events | Yes | Skipped signals, missing-feature events, or rejected transition inputs. |

## Behavior

When flat and selection emits one target, allocate all settled cash to a
next-session entry order. After entry, maintain a full-position sell limit at
`entry_price × 1.0521`.

At every completed trading-session close, including the entry session, compare
that session's adjusted close with that same session's point-in-time SMA50.
When `adjusted_close < sma_50`, record an after-close invalidation signal and
emit a full-position market-on-open sell for the next valid session. Equality
does not signal. This is a below-state rule; it does not require the preceding
session to have been above SMA50.

An intraday profit-limit fill known before the close completes the position and
cancels SMA50 monitoring. If a prior SMA50 signal is pending, its next-open
liquidation executes before considering that new session's high. At session 126
after entry, cancel remaining exit orders and liquidate at that session's
close. Ignore and report new selection intents while a position is active.

## Parameters

| name | type | required | default | constraints | description |
| --- | --- | --- | --- | --- | --- |
| `profit_return` | decimal | No | `0.0521` | Fixed by descriptor; positive decimal return. | Entry-relative full-position profit target. |
| `sma_window` | positive trading-day count | No | `50` | Fixed by descriptor. | Moving-average window used for daily invalidation. |
| `sma_signal_operator` | enum | No | `close_below` | Fixed by descriptor; strict `<`. | Signals when the completed adjusted close is below same-session SMA50. |
| `sma_signal_execution` | enum | No | `next_session_open` | Fixed by descriptor. | Prevents a same-close look-ahead fill. |
| `maximum_holding_days` | positive trading-day count | No | `126` | Fixed by descriptor. | Session count triggering mandatory liquidation. |
| `active_position_signal_behavior` | enum | No | `ignore_and_report` | Fixed by descriptor. | Skips new selections while holding a position. |
| `cash_allocation` | enum | No | `all_settled_cash` | Fixed by descriptor. | Concentrates available capital in the selected target. |

## Data Requirements

Requires adjusted daily open, high, close, a point-in-time SMA50 computed from
actual observations, an exchange-session calendar, position/order state, and
settled/unsettled cash. Missing daily observations are not forward-filled.

## Point-in-Time Rules

The current session's close and SMA50 become observable only after that close.
Therefore an SMA50 liquidation cannot fill before the following valid session's
open. The SMA50 must use only observations through the signal session. Entry
selection remains governed by its configured
[trigger](../OPERATIONS.md#trigger); daily monitoring does
not rerank the universe or authorize daily entries.

## Failure Behavior

If close or SMA50 is missing, retain the position, emit a
`missing_sma50_state` constraint event, and retry on the next valid completed
row. Reject multiple selection targets or invalid quantities. If a next-open
or horizon liquidation is rejected, retain and report the position until
[execution](../OPERATIONS.md#execution-and-execution-models) succeeds.

## Benchmark Contract

Replay identical daily feature, selection-intent, and account-state tapes.
Verify entry-day monitoring, strict below/equality behavior, no same-close
fill, next-open priority, profit-target cancellation, horizon enforcement, and
missing-feature handling. Compare return, drawdown, tail loss, turnover,
whipsaw rate, exposure, and cash drag against no SMA50 exit, an actual
above-to-below crossing rule, and confirmation variants.

## Implementation

`scripts/backtests/strategies/technical_resistance_runner.py`

The `run(...)` event loop implements this descriptor when
`exit_variant=full_at_5_21_sma50_exit`; `sma50_below_exit_signal(...)` and
`sma50_next_open_exit_due(...)` expose its directly testable signal timing.
