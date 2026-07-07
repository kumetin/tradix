# Component Test: Single Position Rotation

Component: [Single Position Rotation](../../portfolio-policies/single-position-rotation.md)

## Purpose

Verify that the portfolio holds one selected ticker at a time and only rotates
when the selected ticker changes.

## Expected Behavior

| Case | Given | Expected |
| --- | --- | --- |
| First selection | No current holdings and selected ticker `AAPL` | Buy `AAPL` using available cash according to the execution model. |
| Same selection | Current holding `AAPL`, selected ticker `AAPL` | Do not sell. Add any new cash to `AAPL`. |
| New selection | Current holding `AAPL`, selected ticker `MSFT` | Sell `AAPL`; replacement buy timing is controlled by the execution model. |
| No settled proceeds | Current holding sold but proceeds are unsettled | Wait for execution model before buying replacement ticker. |
| Selection fallback | Selection model returns fallback ticker | Treat fallback ticker like any other selected ticker. |

## Metrics

| Metric | Meaning |
| --- | --- |
| `position_count_max` | Should never exceed `1` after fills settle. |
| `rotation_count` | Number of times selected ticker changed. |
| `cash_wait_days` | Days in cash due to execution model settlement. |
| `unintended_sell_count` | Should be `0` when selected ticker is unchanged. |

## Pass Criteria

- The policy never intentionally holds more than one selected position.
- It does not sell when the selected ticker is unchanged.
- It does not assume replacement buys can use unsettled proceeds.
