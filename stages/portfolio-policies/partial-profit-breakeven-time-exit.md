# Partial Profit Breakeven Time Exit

## ID

`partial-profit-breakeven-time-exit`

## Stage Type

`portfolio-policy`

## Purpose

Manage positions received from
[selection](../OPERATIONS.md#selection-and-selection-models) with an initial protective stop, partial profit
realization, a breakeven stop on the remainder, an opportunity-cost time stop,
and a final holding horizon.

## Input Contract

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `as_of` | trading date or timestamp | Yes | Transition decision time. |
| `selection_intent` | ordered target ticker/weight pairs | Yes | Upstream desired exposure. |
| `portfolio_state` | positions and lots | Yes | Entry price/session, original and remaining quantities, and order state. |
| `cash_state` | settled and unsettled ledger | Yes | Cash available under account rules. |
| `daily_market_state` | map of held instrument to adjusted OHLC | Conditional | Completed bar for active holdings. |
| `session_index` | exchange-session index | Yes | Actual sessions since each entry fill. |

## Output Contract

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `as_of` | trading date or timestamp | Yes | Input time echoed. |
| `orders` | ordered order intents | Yes | Entries, partial limits, protective stops, or time/horizon liquidations. |
| `retained_positions` | instrument IDs with reasons | Yes | Positions deliberately retained. |
| `unallocated_cash` | amount with reason | Yes | Cash not assigned. |
| `constraint_events` | ordered events | Yes | Invalid state, skipped intent, or ambiguous-bar decisions. |

## Behavior

Allocate toward the equal-weight
[selection](../OPERATIONS.md#selection-and-selection-models) intent using settled cash. For each
filled lot, set an initial full-position stop at `entry_price × 0.925` and a
partial profit limit at `entry_price × 1.225`. If the partial target fills,
sell 50% of original quantity and replace the remaining protective stop with a
breakeven stop at the original entry price.

At session 15, liquidate a position whose completed adjusted close is no
higher than its entry price. Do not apply that opportunity-cost exit to a
position already above entry. Liquidate every remaining share at session 378.
When a daily bar touches both a stop and target and intraday order is unknown,
apply the stop first. A gap through a stop fills at the worse adjusted open.

The values encode a research instance of the supplied blueprint and do not
define a [trigger](../OPERATIONS.md#trigger); they are not
claims that a 3:1 reward/risk ratio or a particular win rate has been achieved.

## Parameters

| name | type | required | default | constraints | description |
| --- | --- | --- | --- | --- | --- |
| `initial_stop_return` | decimal | No | `0.075` | Fixed by descriptor; `(0,1)`. | Initial loss distance. |
| `partial_profit_return` | decimal | No | `0.225` | Fixed by descriptor; positive. | Midpoint of the proposed 20%–25% profit zone. |
| `partial_sale_fraction` | decimal | No | `0.50` | Fixed by descriptor; `(0,1)`. | Original quantity sold at the profit target. |
| `remainder_stop` | enum | No | `entry_price` | Fixed by descriptor. | Stop applied after the partial fill. |
| `stagnation_sessions` | positive trading-day count | No | `15` | Fixed by descriptor. | Approximately three trading weeks. |
| `stagnation_rule` | enum | No | `close_at_or_below_entry` | Fixed by descriptor. | Defines an unchanged or losing position. |
| `maximum_holding_sessions` | positive trading-day count | No | `378` | Fixed by descriptor; greater than `stagnation_sessions`. | Eighteen-month upper bound. |
| `ambiguous_bar_priority` | enum | No | `stop_first` | Fixed by descriptor. | Conservative daily-bar ordering. |
| `gap_stop_fill` | enum | No | `worse_of_open_or_stop` | Fixed by descriptor. | Models stop gap risk. |

## Data Requirements

Requires adjusted daily OHLC, actual exchange sessions, immutable entry data,
original/remaining quantities, open-order state, and settled/unsettled cash.

## Point-in-Time Rules

Levels are fixed from the actual entry fill. Only completed post-entry bars may
trigger transitions. No future high, close, or revised signal may reset entry,
target, stop, or session count.

## Failure Behavior

Reject invalid target weights or lot state and report a constraint event.
Missing bars retain and report the position without inferred fills. Rejected
liquidations remain open until [execution](../OPERATIONS.md#execution-and-execution-models)
succeeds.

## Benchmark Contract

Replay identical selection/account/bar tapes and compare full holding,
full-profit liquidation, fixed 7.5% stop only, partial profit without time stop,
and this policy. Measure expectancy, CAGR, drawdown, tail/gap loss, turnover,
cash drag, target/stop/time-exit rates, and deterministic cash conservation.

## Implementation

`stages/portfolio-policies/partial_profit_breakeven_time_exit.py`

The public `transition(...)` function is pure and stateless. The strategy
runner supplies the current selection, lots, cash, completed daily bars, and
per-position session counts, then applies the returned order intents through
its execution model.
