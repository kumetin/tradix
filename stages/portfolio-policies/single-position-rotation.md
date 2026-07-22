# Single Position Rotation

The portfolio holds one selected ticker at a time.

## Sell [Trigger](../OPERATIONS.md#trigger)

At each scheduled allocation cycle, the strategy selects a target ticker from
the configured universe. If the target ticker differs from the currently held
ticker, sell the current position at the scheduled [execution](../OPERATIONS.md#execution-and-execution-models) point.

The scheduled execution point is:

- next trading day adjusted open after the entry rule appears, or
- month-end adjusted open if the entry rule does not appear during the month

The replacement buy is controlled by the execution model. A frictionless or
margin-style execution model may allow the sell and buy at the same execution
point. A cash-account execution model should wait until sale proceeds are
settled before buying the replacement ticker.

If the selected ticker is already held, do not sell it. Add any new cash to the
existing position at the execution point.

## Cash Handling

Sale proceeds and new cash are allocated to the selected ticker, subject to the
execution model.

| Setting | Value |
| --- | --- |
| `allow_selling` | `true` |
| `position_policy` | Single selected ticker |
