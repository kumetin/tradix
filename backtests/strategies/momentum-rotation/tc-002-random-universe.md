# TC-002: Random Universe

Strategy: [Momentum Rotation](../../../strategies/momentum-rotation.md)

Strategy Flow: [Momentum Rotation Flow](../../../strategies/momentum-rotation.flow.md)

## Edge Being Tested

This test case evaluates whether the momentum-rotation rules can produce
organic capital growth when applied to a broad, non-curated stock universe
rather than a universe selected for high-beta momentum characteristics.

The expected edge has three parts:

- Use a reproducibly random set of 20 stocks to reduce universe-selection bias.
- Rotate the portfolio into the selected ticker instead of accumulating every
  prior selection indefinitely.
- Apply the same momentum, trend-health, drawdown, and pullback-entry rules used
  by the high-beta setup.

This is primarily a robustness and baseline test. If the strategy only works on
the curated high-beta universe, this case should expose that dependency.

## Universe

[Random 20 Non-Curated 1](../../../universes/random-20-non-curated-1.md)

## Selection Model

[SMA Drawdown Trailing Return](../../../selection-models/sma-drawdown-trailing-return.md)

| Parameter | Value |
| --- | --- |
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

## Funding

[Initial 5000 Monthly 100](../../../funding-profiles/initial-5000-monthly-100.md)

## Portfolio Policy

[Single Position Rotation](../../../portfolio-policies/single-position-rotation.md)

The sell trigger is defined by the portfolio policy. In this setup, the current
position is sold when a different ticker is selected. The replacement buy waits
for settled cash according to the execution model.

## Execution and Accounting

[IBKR Cash T+1](../../../execution-models/ibkr-cash-t-plus-one.md)

This execution model does not reuse unsettled sale proceeds. A rotation may
therefore spend one or more trading sessions in cash before buying the newly
selected ticker.

## Evaluation

[TC-002 Full Period](../../../evaluations/momentum-rotation/tc-002-full-period.md)

## Benchmarks

- `SPY` buy and hold
- Equal-weight [Random 20 Non-Curated 1](../../../universes/random-20-non-curated-1.md)
  universe
