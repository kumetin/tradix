# IBKR Cash T+1

[Execution model](../OPERATIONS.md#execution-and-execution-models) for a cash-style Interactive Brokers account where stock sale
proceeds are not reused until they are settled.

## Settlement Assumption

U.S. stock trades settle on `T+1`: one business day after trade date. Sale
proceeds from a stock position become available for a replacement stock purchase
on the next business day after the sale, subject to holidays, account currency,
FX conversion, and IBKR account restrictions.

## Rotation Handling

When a [portfolio policy](../OPERATIONS.md#portfolio-transitions-and-portfolio-policies) calls for selling the current position and buying a new
selected ticker:

1. Sell the current position at the scheduled execution price.
2. Wait until sale proceeds are settled.
3. Buy the new selected ticker with settled proceeds and any settled new cash.

This means a rotation can spend one or more trading sessions in cash.

## Settings

| Setting | Value |
| --- | --- |
| `fractional_shares` | `true` |
| `fees` | `0` |
| `taxes` | `0` |
| `slippage` | `0` |
| `settlement_lag` | `T+1` |
| `reuse_unsettled_sale_proceeds` | `false` |
