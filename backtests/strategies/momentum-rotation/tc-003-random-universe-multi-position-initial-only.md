# TC-003: Random Universe Multi-Position Initial Only

Strategy: [Momentum Rotation](../../../strategies/momentum-rotation.md)

Strategy Flow: [Momentum Rotation Flow](../../../strategies/momentum-rotation.flow.md)

## Edge Being Tested

This test case checks whether momentum rotation can grow a fixed initial capital
base without recurring contributions while holding multiple positions at the
same time.

The expected edge has three parts:

- Use the same reproducibly random 20-stock universe as TC-002.
- Select the top eligible momentum names instead of only one ticker.
- Rotate toward equal-weight target positions using only the initial capital and
  settled sale proceeds.

This setup is closer to a conventional portfolio rotation test than TC-001's
new-money accumulation or TC-002's single-position rotation.

## Universe

[Random 20 Non-Curated 1](../../../universes/random-20-non-curated-1.md)

## Selection Model

[Top N SMA Drawdown Trailing Return](../../../selection-models/top-n-sma-drawdown-trailing-return.md)

| Parameter | Value |
| --- | --- |
| `target_count` | `5` |
| `medium_sma_window` | `50` trading days |
| `long_sma_window` | `200` trading days |
| `rolling_high_window` | `252` trading days |
| `max_drawdown` | `-45%` |
| `ranking_return_window` | `126` trading days |

## Strategy Parameters

| Parameter | Value |
| --- | --- |
| `entry_down_days` | `4` |
| `entry_fallback` | Buy at month-end adjusted open |

## Trigger

[Monthly Allocation](../../../triggers/monthly-allocation.md)

The trigger supplies monthly allocation cycles, but the funding profile does
not add monthly cash after the initial allocation.

## Funding

[Initial 5000 Only](../../../funding-profiles/initial-5000-only.md)

## Portfolio Policy

[Multi Position Target Weight Rotation](../../../portfolio-policies/multi-position-target-weight-rotation.md)

This policy sells positions that leave the target set and rotates toward the
equal-weight targets returned by the selection model.

## Execution and Accounting

[IBKR Cash T+1](../../../execution-models/ibkr-cash-t-plus-one.md)

This execution model does not reuse unsettled sale proceeds. A rotation may
therefore spend one or more trading sessions partially or fully in cash before
buying replacement positions.

## Evaluation

[TC-003 Full Period](../../../evaluations/momentum-rotation/tc-003-full-period.md)

## Benchmarks

- `SPY` buy and hold
- Equal-weight [Random 20 Non-Curated 1](../../../universes/random-20-non-curated-1.md)
  universe
