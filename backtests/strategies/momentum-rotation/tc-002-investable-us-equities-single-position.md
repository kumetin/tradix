# TC-002: Investable US Equities Single-Position Rotation

Strategy: [Momentum Rotation](../../../strategies/momentum-rotation.md)

## Edge Being Tested

### Thesis Claim Under Test

The intermediate-momentum continuation claim should survive outside an index
membership set when applied to a broad, point-in-time investable US common-stock
population. The highest-ranked eligible candidate is expected to outperform the
equal-weight dated universe over the next allocation cycle.

The expected edge has three parts:

- Resolve up to 1,000 candidates from explicit point-in-time classification,
  investability, data-sufficiency, and float-market-cap coverage rules.
- Rotate the portfolio into the selected ticker instead of accumulating every
  prior [selection](../../../stages/OPERATIONS.md#selection-and-selection-models) indefinitely.
- Apply the same momentum, trend-health, drawdown, and pullback-entry rules used
  by a hand-curated momentum setup.

### Portfolio Expression

This is primarily a universe-robustness test expressed through concentrated
single-position rotation. Rotation, settlement delay, and concentration affect
realized portfolio results, but they are not substitutes for measuring the
selection model's same-date forward relative performance.

### Evidence Against the Claim

The thesis is weakened if rank quality and top-selection excess return disappear
in the broader universe, if results depend on a few securities or one regime,
or if realistic rotation costs and settlement eliminate the observed edge.

## Universe

[Investable US Equities Top 1000](../../../stages/universe-models/investable-us-equities-top-1000.md)

## Selection Model

[SMA Drawdown Trailing Return](../../../stages/selection-models/sma-drawdown-trailing-return.md)

| Parameter | Value |
| --- | --- |
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

## [Funding](../../../stages/OPERATIONS.md#funding-profiles)

[Initial 5000 Monthly 100](../../../configuration/funding/initial-5000-monthly-100.md)

## [Portfolio Policy](../../../stages/OPERATIONS.md#portfolio-transitions-and-portfolio-policies)

[Single Position Rotation](../../../stages/portfolio-policies/single-position-rotation.md)

The sell trigger is defined by the portfolio policy. In this setup, the current
position is sold when a different ticker is selected. The replacement buy waits
for settled cash according to the [execution model](../../../stages/OPERATIONS.md#execution-and-execution-models).

## Execution and Accounting

[IBKR Cash T+1](../../../stages/execution-models/ibkr-cash-t-plus-one.md)

This execution model does not reuse unsettled sale proceeds. A rotation may
therefore spend one or more trading sessions in cash before buying the newly
selected ticker.

## [Evaluation](../../../stages/OPERATIONS.md#evaluation-plans)

[TC-002 Full Period](../../../configuration/evaluations/momentum-rotation/tc-002-full-period.md)

## Benchmarks

- `SPY` buy and hold
- Equal-weight investable-US-equities universe resolved at each allocation date
