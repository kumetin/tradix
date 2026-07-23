# Daily-Bar Frictionless Fractional

## ID

`daily-bar-frictionless-fractional`

## Stage Type

`execution-model`

## Purpose

Provide deterministic research
[execution](../OPERATIONS.md#execution-and-execution-models) fills for
next-session entries, resting limit
exits, and horizon liquidations using adjusted daily bars and fractional shares
without costs.

## Input Contract

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `submitted_at` | timestamp | Yes | Order submission time. |
| `orders` | ordered order intents | Yes | Market-on-open, limit, cancellation, or market-on-close requests. |
| `market_tape` | adjusted daily OHLCV bars | Yes | Bars visible to the simulator in chronological order. |
| `calendar` | exchange-session calendar | Yes | Valid sessions and ordering. |
| `account_state` | positions and cash ledger | Yes | Pre-fill quantities and settled cash. |

## Output Contract

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `fills` | ordered fill records | Yes | Instrument, quantity, adjusted price, session, and order ID. |
| `rejections` | ordered records | Yes | Invalid, unaffordable, or unavailable-bar orders. |
| `cash_ledger` | dated movements | Yes | Immediate proceeds and purchase debits. |
| `account_state` | positions and cash ledger | Yes | State after fills. |

## Behavior

Fill an entry submitted after a decision close at the next valid session's
adjusted open. Fill a sell limit at its limit price on the first later session
whose adjusted high is at least the limit. Fill horizon liquidation at that
session's adjusted close. Allow fractional quantities and reject negative or
over-position sells. Fees, taxes, and slippage are zero.

## Parameters

| name | type | required | default | constraints | description |
| --- | --- | --- | --- | --- | --- |
| `fractional_shares` | boolean | No | `true` | Fixed by descriptor. | Allows fractional quantities. |
| `fees` | decimal | No | `0` | Fixed by descriptor; non-negative currency amount. | Per-order fees. |
| `taxes` | decimal | No | `0` | Fixed by descriptor; non-negative currency amount. | Taxes charged by the model. |
| `slippage` | decimal | No | `0` | Fixed by descriptor; decimal return. | Price slippage. |
| `settlement_lag` | non-negative session count | No | `0` | Fixed by descriptor. | Makes sale proceeds immediately settled. |
| `reuse_unsettled_sale_proceeds` | boolean | No | `true` | Fixed by descriptor. | Consistent with zero settlement lag. |
| `limit_gap_fill_rule` | enum | No | `at_limit` | Fixed by descriptor. | Conservatively gives no favorable price improvement through a target. |

## Data Requirements

Complete adjusted daily open, high, low, and close values plus a compatible
exchange-session calendar are required. Corporate-action adjustment must be
consistent across signals, targets, and fills.

## Point-in-Time Rules

An order cannot fill before submission or from the bar that produced an
after-close signal. Resting limit orders inspect only later bars in chronological
order. Horizon-close fills use the close only after that session completes.

## Failure Behavior

Reject orders when a required bar field, position quantity, or cash value is
missing. Do not forward-fill prices or infer intraday paths. A sell limit needs
only the high-side touch because this model has no simultaneous stop order.

## Benchmark Contract

Replay fixed order and adjusted-bar tapes. Verify next-session timing, first
limit touch, fractional accounting, horizon session count, target cancellation,
cash conservation, missing-bar rejection, and deterministic repeatability.

## Implementation

`scripts/backtests/strategies/technical_resistance_runner.py`

The `run(...)` event loop implements next-session adjusted-open entry,
first-later-session limit touch, fractional cash accounting, and adjusted-close
horizon fills.
