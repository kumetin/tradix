# TC-003: Investable US Equities Multi-Position Initial Only

Strategy: [Momentum Rotation](../../../strategies/momentum-rotation.md)

## Edge Being Tested

### Thesis Claim Under Test

If momentum rank contains a graded continuation signal rather than only a lucky
top-name effect, several of the highest-ranked eligible candidates should retain
positive excess performance when held together. The thesis should therefore
survive lower concentration and fixed-capital portfolio rotation.

The expected edge has three parts:

- Use the same point-in-time investable US equities universe as TC-002.
- Select the top eligible momentum names instead of only one ticker.
- Rotate toward equal-weight target positions using only the initial capital and
  settled sale proceeds.

### Portfolio Expression

This setup expresses the same signal through five equal-weight targets using
fixed initial capital. Target count, equal weighting, and absence of recurring
[funding](../../../stages/OPERATIONS.md#funding-profiles) are robustness dimensions rather than separate claims about market
predictability.

### Evidence Against the Claim

The claim is weakened if excess return exists only for one selected name, if
rank buckets are not monotonic, if diversification removes the effect, or if
turnover, settlement, and cash drag eliminate it.

## Universe

[Investable US Equities Top 1000](../../../stages/universe-models/investable-us-equities-top-1000.md)

## [Selection Model](../../../stages/OPERATIONS.md#selection-and-selection-models)

[Top N SMA Drawdown Trailing Return](../../../stages/selection-models/top-n-sma-drawdown-trailing-return.md)

| Parameter | Value |
| --- | --- |
| `target_count` | `5` |
| `medium_sma_window` | `50` trading days |
| `long_sma_window` | `200` trading days |
| `rolling_high_window` | `252` trading days |
| `max_drawdown` | `-45%` |
| `ranking_return_window` | `126` trading days |
| `fallback_ticker` | `SPY` |

## Strategy Parameters

| Parameter | Value |
| --- | --- |
| `entry_down_days` | `4` |
| `entry_fallback` | Buy at month-end adjusted open |

## [Trigger](../../../stages/OPERATIONS.md#trigger)

[Monthly Allocation](../../../configuration/triggers/monthly-allocation.md)

The trigger supplies monthly allocation cycles, but the funding profile does
not add monthly cash after the initial allocation.

## Funding

[Initial 5000 Only](../../../configuration/funding/initial-5000-only.md)

## [Portfolio Policy](../../../stages/OPERATIONS.md#portfolio-transitions-and-portfolio-policies)

[Multi Position Target Weight Rotation](../../../stages/portfolio-policies/multi-position-target-weight-rotation.md)

This policy sells positions that leave the target set and rotates toward the
equal-weight targets returned by the selection model.

## [Execution](../../../stages/OPERATIONS.md#execution-and-execution-models) and Accounting

[IBKR Cash T+1](../../../stages/execution-models/ibkr-cash-t-plus-one.md)

This execution model does not reuse unsettled sale proceeds. A rotation may
therefore spend one or more trading sessions partially or fully in cash before
buying replacement positions.

## [Evaluation](../../../stages/OPERATIONS.md#evaluation-plans)

[TC-003 Full Period](../../../configuration/evaluations/momentum-rotation/tc-003-full-period.md)

## Benchmarks

- `SPY` buy and hold
- Equal-weight investable-US-equities universe resolved at each allocation date
