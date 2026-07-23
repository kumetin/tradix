# TC-001: Point-in-Time S&P 500 Top-10 Monthly Rotation

Strategy:
[Classic 12-1 Momentum Rotation](../../../strategies/classic-12-1-momentum-rotation.md)

## Configuration Intent

### Strategy Behavior Implemented

This scenario converts the validated cross-sectional selector into a complete
portfolio test. At each monthly cutoff it ranks the dated S&P 500 membership
by classic 12–1 momentum and rotates toward the ten strongest eligible names.

The top-ten count is frozen from the component validation rather than selected
from this scenario's portfolio results. Equal weighting reduces dependence on
one extreme observation. No trend filter, market gate, stop, or delayed-entry
rule is added.

### Portfolio Expression

The account begins with fixed capital, holds up to ten equal-weight positions,
and receives no later contributions. Positions that remain selected are
rebalanced; positions leaving the target set are sold. Replacement purchases
wait for settled proceeds.

### Evaluation Sensitivities

Profitability is not sufficient by itself. The result is weakened by failure
to beat SPY or the dated equal-weight universe, excessive drawdown or turnover,
concentration in a few names, incomplete departed-security outcomes, or
material sensitivity to plausible costs.

## Universe

[Point-in-Time S&P 500](../../../stages/universe-models/point-in-time-sp500.md)

## [Selection Model](../../../stages/OPERATIONS.md#selection-and-selection-models)

[Classic 12-1 Momentum](../../../stages/selection-models/classic-12-1-momentum.md)

| Parameter | Value |
| --- | --- |
| `target_count` | `10` |
| `fallback_mode` | `empty` |
| `lookback_sessions` | `252` |
| `skip_sessions` | `21` |

## Strategy Parameters

None. The signal definition is frozen by the strategy and selector; target
count is portfolio expression.

## [Trigger](../../../stages/OPERATIONS.md#trigger)

[Monthly Allocation](../../../configuration/triggers/monthly-allocation.md)

## [Funding](../../../stages/OPERATIONS.md#funding-profiles)

[Initial 5000 Only](../../../configuration/funding/initial-5000-only.md)

## [Portfolio Policy](../../../stages/OPERATIONS.md#portfolio-transitions-and-portfolio-policies)

[Multi Position Target Weight Rotation](../../../stages/portfolio-policies/multi-position-target-weight-rotation.md)

## [Execution](../../../stages/OPERATIONS.md#execution-and-execution-models) and Accounting

[IBKR Cash T+1](../../../stages/execution-models/ibkr-cash-t-plus-one.md)

Signals use the last completed session before the monthly allocation cycle.
Sales execute no earlier than the next session. Replacement purchases use
settled cash, so the account may temporarily remain underinvested.

## [Evaluation](../../../stages/OPERATIONS.md#evaluation-plans)

[TC-001 Post-Validation Confirmation](../../../configuration/evaluations/classic-12-1-momentum-rotation/tc-001-post-validation-confirmation.md)

## Benchmarks

- SPY buy and hold from the same initial capital and entry date
- Dated equal-weight point-in-time S&P 500 with the same rebalance cadence
- Equal-weight eligible universe
- Frozen-seed random ten-stock monthly rotations

## Metrics

- terminal value, total return, CAGR, and calendar-year return;
- volatility, Sharpe ratio, maximum drawdown, and time under water;
- excess return and tracking error versus SPY and the dated universe;
- turnover, trade count, settlement cash drag, and cost sensitivity;
- position, ticker, sector, and calendar-year concentration;
- monthly hit rate and rolling 12-month excess return; and
- candidate coverage, exclusions, and missing terminal-return exposure.

## Output Location

Generated artifacts belong under:

```text
artifacts/stock/backtests/strategies/classic-12-1-momentum-rotation/tc-001/<run-directory>/
```
