# Component Test: Multi Position Target Weight Rotation

Component: [Multi Position Target Weight Rotation](../../stages/portfolio-policies/multi-position-target-weight-rotation.md)

## Purpose

Verify that the portfolio rotates toward a multi-position target allocation
supplied by a [selection model](../../stages/OPERATIONS.md#selection-and-selection-models).

## Expected Behavior

| Case | Given | Expected |
| --- | --- | --- |
| Initial target set | No holdings and five equal-weight targets | Buy target positions using available cash according to the [execution model](../../stages/OPERATIONS.md#execution-and-execution-models). |
| Name drops out | Holding `AAPL`, new target set excludes `AAPL` | Sell `AAPL` at the scheduled execution point. |
| Name remains | Holding `AAPL`, new target set includes `AAPL` near target weight | Keep `AAPL`; no unnecessary sell. |
| Above target | Holding `AAPL` is materially above target weight | Sell enough to move toward target weight when rebalancing is required. |
| Below target | Holding `AAPL` is below target weight | Buy or add using settled cash. |
| Fewer targets | Selection model returns fewer than target count | Allocate across returned targets only. |
| Settlement delay | Replacement buys need sale proceeds from dropped names | Wait for settled cash under cash-account execution models. |

## Metrics

| Metric | Meaning |
| --- | --- |
| `position_count` | Number of holdings after rebalance. |
| `weight_drift_avg` | Average absolute distance from target weights. |
| `turnover` | Gross value traded divided by portfolio value. |
| `cash_drag` | Percent of portfolio held in cash due to settlement or allocation limits. |
| `dropped_name_hold_count` | Should be `0` after sells settle. |

## Pass Criteria

- Positions converge toward target weights after settlement.
- Names outside the target set are sold.
- The policy respects settled-cash constraints from the execution model.
