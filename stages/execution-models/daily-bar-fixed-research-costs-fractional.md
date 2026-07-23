# Daily-Bar Fixed Research Costs Fractional

## ID

`daily-bar-fixed-research-costs-fractional`

## Stage Type

`execution-model`

## Purpose

Provide deterministic adjusted-daily-bar
[execution](../OPERATIONS.md#execution-and-execution-models) with fractional
shares, 10 basis points of adverse price slippage per fill, and a fixed $1 fee
per order.

## Input Contract

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `submitted_at` | timestamp | Yes | Order submission time. |
| `orders` | ordered order intents | Yes | Market-open, limit, stop, or market-close orders. |
| `market_tape` | adjusted daily OHLCV bars | Yes | Chronological point-in-time bars. |
| `calendar` | exchange-session calendar | Yes | Valid sessions. |
| `account_state` | positions and cash ledger | Yes | Pre-fill account state. |

## Output Contract

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `fills` | ordered fill records | Yes | Quantity, adjusted price, session, and order ID. |
| `rejections` | ordered records | Yes | Invalid or unavailable fills. |
| `cash_ledger` | dated movements | Yes | Debits, proceeds, and fees. |
| `account_state` | positions and cash ledger | Yes | Post-fill state. |
| `costs` | fee and slippage breakdown | Yes | Attributed modeled friction. |

## Behavior

Apply 10 bps adverse slippage to every buy and sell fill, then charge $1 per
filled order. Apply conservative stop gap-through and stop-first ambiguous-bar
rules supplied by the policy. Settlement lag is zero and fractional shares are
allowed.

## Parameters

| name | type | required | default | constraints | description |
| --- | --- | --- | --- | --- | --- |
| `fractional_shares` | boolean | No | `true` | Fixed. | Allows fractional quantities. |
| `slippage_bps` | non-negative decimal | No | `10` | Fixed basis points per fill. | Adverse price adjustment. |
| `fee_per_order` | non-negative currency | No | `1` | Fixed USD amount. | Per-filled-order fee. |
| `settlement_lag` | non-negative session count | No | `0` | Fixed. | Immediate settlement. |
| `reuse_unsettled_sale_proceeds` | boolean | No | `true` | Fixed with zero lag. | Allows immediate reuse. |

## Data Requirements

Requires adjusted daily OHLC, compatible calendar, quantities, and cash.

## Point-in-Time Rules

Orders cannot inspect or fill from bars before submission. After-close signals
fill no earlier than the next valid session.

## Failure Behavior

Reject missing-bar, negative-quantity, and unaffordable orders. Do not
forward-fill prices.

## Benchmark Contract

Replay fixed order/bar tapes and verify fill timing, adverse price adjustment,
fees, stop gaps, cash conservation, and deterministic repeatability against
the frictionless model.

## Implementation

`scripts/backtests/strategies/technical_resistance_runner.py`

Use `slippage_bps=10` and `fee_per_order=1`.
