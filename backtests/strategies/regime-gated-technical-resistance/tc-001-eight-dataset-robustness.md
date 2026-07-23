# TC-001: Eight-Dataset Robustness

Strategy: [Regime-Gated Technical Resistance](../../../strategies/regime-gated-technical-resistance.md)

## Configuration Intent

Whether SPY SMA200 gating plus a 15% full stop materially improves tail risk
while preserving competitive return versus the identical ungated/no-stop
strategy.

## Configuration Delta

Fix the score, +5.21% target, 126-session horizon, costs, funding, and entry
timing. Compare only the combined market gate and stop against the baseline
over five universes and three distinct historical windows.

## [Static Universe](../../../stages/OPERATIONS.md#universe-resolution-and-universe-models)

Use [Random Universe 1](../../../configuration/universes/random-sp500-50-1.md)
through [Random Universe 5](../../../configuration/universes/random-sp500-50-5.md)
as separately reported replications. Historical windows use universe 1.

## [Selection Model](../../../stages/OPERATIONS.md#selection-and-selection-models)

[Technical Resistance Score SPY SMA200 Gated](../../../stages/selection-models/technical-resistance-score-spy-sma200-gated.md)

## [Trigger](../../../stages/OPERATIONS.md#trigger)

[Monthly Allocation](../../../configuration/triggers/monthly-allocation.md)

Use the completed prior-session decision cutoff and next-session execution.

## [Portfolio Policy](../../../stages/OPERATIONS.md#portfolio-transitions-and-portfolio-policies)

[Single Position Profit Fixed Stop Horizon Exit](../../../stages/portfolio-policies/single-position-profit-fixed-stop-horizon-exit.md)

## [Execution](../../../stages/OPERATIONS.md#execution-and-execution-models)

[Daily-Bar Fixed Research Costs Fractional](../../../stages/execution-models/daily-bar-fixed-research-costs-fractional.md)

## [Funding](../../../stages/OPERATIONS.md#funding-profiles)

[Initial 5000 Only](../../../configuration/funding/initial-5000-only.md)

## [Evaluation](../../../stages/OPERATIONS.md#evaluation-plans)

[Eight-Dataset Robustness](../../../configuration/evaluations/regime-gated-technical-resistance/tc-001-eight-dataset-robustness.md)

## Benchmarks

- SPY buy and hold
- Equal-weight evaluated universe
- Identically costed ungated/no-stop +5.21% baseline

## Metrics

- CAGR, total return, maximum and worst drawdown;
- positive-dataset count and median result;
- paired baseline differences;
- SPY and equal-weight benchmark wins;
- target, stop, and horizon exit counts; and
- modeled cost sensitivity.

## Output Location

```text
artifacts/stock/backtests/strategies/technical-resistance-runner/autonomous-costs/
```
