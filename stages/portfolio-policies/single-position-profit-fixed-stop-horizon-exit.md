# Single Position Profit Fixed Stop Horizon Exit

## ID

`single-position-profit-fixed-stop-horizon-exit`

## Stage Type

`portfolio-policy`

## Purpose

Own a concentrated single-position
[portfolio transition](../OPERATIONS.md#portfolio-transitions-and-portfolio-policies)
with a full +5.21% profit target, full 15% protective stop, and 126-session
maximum horizon.

## Input Contract

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `as_of` | trading date or timestamp | Yes | Transition time. |
| `selection_intent` | zero or one target | Yes | Upstream target and weight. |
| `portfolio_state` | positions and lots | Yes | Entry price/session, quantity, and order state. |
| `cash_state` | settled and unsettled ledger | Yes | Available cash. |
| `daily_market_state` | adjusted daily OHLC row | Conditional | Open, high, low, and close while active. |
| `session_index` | exchange-session index | Yes | Sessions since entry. |

## Output Contract

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `as_of` | trading date or timestamp | Yes | Input time echoed. |
| `orders` | ordered order intents | Yes | Entry, profit limit, protective stop, horizon liquidation, or no-op. |
| `retained_positions` | instruments with reasons | Yes | Deliberately retained holdings. |
| `unallocated_cash` | amount with reason | Yes | Cash left idle by a closed selection gate or active constraint. |
| `constraint_events` | ordered events | Yes | Skipped signals, missing bars, or rejected orders. |

## Behavior

When flat and one
[selection](../OPERATIONS.md#selection-and-selection-models) target exists,
allocate all settled cash to next-session-open
entry. After entry, maintain a full-position profit limit at
`entry_price × 1.0521` and a full protective stop at `entry_price × 0.85`.
Inspect later daily bars chronologically.

If adjusted low touches the stop, fill at the stop unless adjusted open is
below it, in which case fill at the worse adjusted open. When a daily bar
touches both stop and profit levels and intraday order is unknowable, give the
stop priority. At session 126, liquidate any remainder at adjusted close.
Ignore and report new selection intents while active.

## Parameters

| name | type | required | default | constraints | description |
| --- | --- | --- | --- | --- | --- |
| `profit_return` | decimal | No | `0.0521` | Fixed; positive. | Full-position profit target. |
| `stop_loss_return` | decimal | No | `0.15` | Fixed; `(0,1)`. | Entry-relative protective stop distance. |
| `maximum_holding_days` | positive trading-day count | No | `126` | Fixed. | Mandatory horizon. |
| `ambiguous_bar_priority` | enum | No | `stop_first` | Fixed. | Conservative same-bar ordering. |
| `gap_stop_fill` | enum | No | `worse_of_open_or_stop` | Fixed. | Models adverse gap-through. |
| `cash_allocation` | enum | No | `all_settled_cash` | Fixed. | Concentrated sizing. |

## Data Requirements

Requires adjusted daily OHLC, an exchange-session calendar, order state, and
cash/position ledgers.

## Point-in-Time Rules

Entry price fixes target and stop for the trade. Levels are never reset from
future prices. Bars are consumed only after entry in chronological order.

## Failure Behavior

Missing required bars retain and report the position without inferred fills.
Rejected liquidation remains open and reported until
[execution](../OPERATIONS.md#execution-and-execution-models) succeeds.

## Benchmark Contract

Replay identical selection/account/bar tapes and compare no stop, 10%, 12%,
15%, and 20% stops on return, drawdown, gap loss, stop rate, turnover, and
deterministic cash conservation.

## Implementation

`scripts/backtests/strategies/technical_resistance_runner.py`

Use `exit_variant=full_at_5_21` and `stop_loss_return=0.15`.
