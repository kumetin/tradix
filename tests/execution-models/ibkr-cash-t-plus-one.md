# Component Test: IBKR Cash T+1

Component: [IBKR Cash T+1](../../execution-models/ibkr-cash-t-plus-one.md)

## Purpose

Verify that a cash-style execution model does not reuse unsettled sale proceeds
and correctly delays replacement buys until settlement.

## Fixtures

Use a trading calendar with:

- Monday, Tuesday, Wednesday as normal trading days
- one market holiday fixture
- at least one Friday-to-Monday transition

## Expected Behavior

| Case | Given | Expected |
| --- | --- | --- |
| Normal sell | Sell order fills on Monday | Sale proceeds become available Tuesday. |
| Friday sell | Sell order fills on Friday | Sale proceeds become available Monday unless Monday is a market holiday. |
| Holiday delay | Sell order fills the day before a market holiday | Sale proceeds become available on the next business trading day after the holiday. |
| Unsettled reuse blocked | A replacement buy is requested before proceeds settle | Buy is delayed or rejected by the execution model. |
| Settled cash allowed | Settled cash is already available | Buy can execute without waiting for sale proceeds. |

## Metrics

| Metric | Meaning |
| --- | --- |
| `settlement_delay_days` | Trading days between sale fill and cash availability. |
| `unsettled_cash_reuse_count` | Should be `0`. |
| `delayed_buy_count` | Number of buys delayed by settlement. |
| `cash_wait_days` | Days spent in cash while waiting for settlement. |

## Pass Criteria

- The model never uses unsettled sale proceeds.
- Settlement dates advance by trading days, not calendar days.
- Holidays and weekends delay availability correctly.
