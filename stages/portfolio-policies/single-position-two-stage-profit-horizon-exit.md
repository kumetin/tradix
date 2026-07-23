# Single Position Two Stage Profit Horizon Exit

## ID

`single-position-two-stage-profit-horizon-exit`

## Stage Type

`portfolio-policy`

## Purpose

Own the [portfolio transition](../OPERATIONS.md#portfolio-transitions-and-portfolio-policies)
for one selected position at a time, realize 75% after a fixed 5.21% surge,
realize the remaining 25% at the setup resistance target, and liquidate any
remainder after a fixed trading-session horizon without a price stop.

## Input Contract

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `as_of` | trading date or timestamp | Yes | Transition decision time. |
| `selection_intent` | zero or one target record | Yes | Upstream [selection](../OPERATIONS.md#selection-and-selection-models) instrument, weight, and fixed resistance target. |
| `portfolio_state` | positions and lots | Yes | Original filled quantity, remaining quantity, entry session, and target-fill state. |
| `cash_state` | settled and unsettled ledger | Yes | Cash available for entry. |
| `session_index` | exchange-session index | Yes | Counts actual trading sessions from entry. |

## Output Contract

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `as_of` | trading date or timestamp | Yes | Input time echoed for traceability. |
| `orders` | ordered order intents | Yes | Entry, sequential profit limits, horizon liquidation, or no-op. |
| `retained_positions` | instrument IDs with reasons | Yes | Position portions intentionally retained through the horizon. |
| `unallocated_cash` | amount with reason | Yes | Cash waiting while a position is active or no target exists. |
| `constraint_events` | ordered events | Yes | Skipped signals, invalid quantities, or expired-order events. |

## Behavior

When flat and selection emits one target, allocate all settled cash to a
next-session entry order. After the entry fill, record `original_quantity`,
entry session, and the immutable resistance target. Emit the first limit sale
for `0.75 × original_quantity` at `entry_price × 1.0521`. Do not activate the
second exit before the first fills. After the first fill, emit a limit sale for
all remaining quantity at the immutable resistance target. If resistance is no
higher than the first fill level, sell the remainder at the first fill level
rather than accepting an inferior price. Ignore later selection cycles while
any quantity from the trade remains open.

Do not emit a price stop. At session 126 after entry, cancel every unfilled
profit order and emit a market liquidation for every remaining share. After complete
liquidation and settlement, wait for the next configured
[trigger](../OPERATIONS.md#trigger) before
entering another selection.

## Parameters

| name | type | required | default | constraints | description |
| --- | --- | --- | --- | --- | --- |
| `first_profit_return` | decimal | No | `0.0521` | Fixed by descriptor; positive decimal return. | Entry-relative price activating the first profit sale. |
| `first_profit_sale_fraction` | decimal | No | `0.75` | Fixed by descriptor; `(0,1)`. | Fraction of original filled quantity sold at the first target. |
| `second_profit_sale_fraction` | decimal | No | `0.25` | Fixed by descriptor; equals `1 - first_profit_sale_fraction`. | Remaining original quantity offered at setup resistance after the first fill. |
| `maximum_holding_days` | positive trading-day count | No | `126` | Fixed by descriptor. | Session count triggering residual liquidation. |
| `allow_price_stop` | boolean | No | `false` | Fixed by descriptor. | Prohibits stop-loss orders. |
| `active_position_signal_behavior` | enum | No | `ignore_and_report` | Fixed by descriptor. | Skips new selections while a trade is active. |
| `cash_allocation` | enum | No | `all_settled_cash` | Fixed by descriptor. | Concentrates available capital in the selected target. |

## Data Requirements

Requires original and remaining quantities, immutable entry and target values,
an exchange trading-session calendar, order status, and settled/unsettled cash.

## Point-in-Time Rules

The target must be supplied by the selection made before entry and must never
be recomputed from post-entry highs. Session count begins only after the entry
fill. Orders may be emitted only from fills and state known at `as_of`.

## Failure Behavior

Reject an intent with multiple targets, missing resistance, invalid quantity,
or nonpositive cash and report a constraint event. If the target never fills,
liquidate the full remaining quantity at the horizon. If liquidation is
rejected, retain and report the position until
[execution](../OPERATIONS.md#execution-and-execution-models) succeeds; do not
silently write it off.

## Benchmark Contract

Replay identical selection and account-state tapes. Compare full resistance
sale, full horizon hold, the prior half-resistance policy, and this sequential
two-stage policy on return, drawdown, tail loss, fill rates, turnover, cash
drag, and deterministic quantity accounting.

## Implementation

`scripts/backtests/strategies/technical_resistance_runner.py`

The `run(...)` event loop owns original-quantity tracking, sequential 75% and
25% profit fills, active-signal skipping, and session-126 liquidation.
