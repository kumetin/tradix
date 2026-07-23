# Regime-Gated Technical Resistance

## Market Thesis

Stocks with strong trend, market-relative strength, controlled pullback, and
nearby resistance can produce frequent modest continuation gains, but the edge
is structurally vulnerable to broad bear regimes and rare six-month collapses.
New risk should be initiated only in a positive long-term market regime and
individual tail loss should be capped.

## Proposed Mechanism

SPY at or above its SMA200 proxies a market environment supportive of
continuation entries. The technical-resistance score selects the strongest
eligible setup. A full +5.21% profit target captures the observed frequent
favorable excursion; a fixed 15% full stop caps individual failure; a
126-session horizon prevents indefinite retention.

## Point-in-Time Observable Proxies

- completed decision-close SPY adjusted close and SMA200;
- candidate adjusted OHLCV, SMA20/50/150, RSI14, volume, support, resistance,
  and 63/126/252-session returns;
- next-session adjusted open for entry;
- later chronological adjusted daily OHLC for target, stop, and horizon fills.

## Prediction Horizon

The selected ticker is expected to reach +5.21% before a 15% loss or 126
trading sessions, conditional on SPY being at or above SMA200.

## Required Component Behavior

The
[selection model](../stages/OPERATIONS.md#selection-and-selection-models)
must emit no target below the SPY SMA200 gate and otherwise preserve the frozen
technical score. The
[portfolio policy](../stages/OPERATIONS.md#portfolio-transitions-and-portfolio-policies)
must fix profit and stop levels from entry, give the stop conservative
same-bar priority, model gap-through, and enforce the horizon. The
[execution model](../stages/OPERATIONS.md#execution-and-execution-models)
must apply declared costs and chronological fill timing.

Compatible stage descriptors:

- [Technical Resistance Score SPY SMA200 Gated](../stages/selection-models/technical-resistance-score-spy-sma200-gated.md)
- [Single Position Profit Fixed Stop Horizon Exit](../stages/portfolio-policies/single-position-profit-fixed-stop-horizon-exit.md)
- [Daily-Bar Fixed Research Costs Fractional](../stages/execution-models/daily-bar-fixed-research-costs-fractional.md)

## Strategy Parameters

| Parameter | Value |
| --- | --- |
| `market_sma_window` | `200` sessions |
| `profit_return` | `0.0521` |
| `stop_loss_return` | `0.15` |
| `maximum_holding_days` | `126` sessions |

## Thesis-Preserving Variations

- point-in-time [universes](../stages/OPERATIONS.md#universe-resolution-and-universe-models)
  and distinct market regimes;
- realistic cost schedules and fractional versus whole-share execution;
- conservative versus known intraday stop/target ordering; and
- fixed capital versus externally configured contribution schedules.

## Thesis-Changing Substitutions

- removing the broad-market regime condition;
- replacing the technical selector with fundamental or value ranking;
- changing the fixed stop into an SMA or discretionary exit;
- partial instead of full profit or stop liquidation;
- resetting levels from post-entry prices; or
- allowing entries while SPY is below SMA200.

## Falsification Criteria

The thesis is weakened or rejected if:

- the overlay does not improve tail behavior across multiple universes and
  bear/recovery regimes;
- aggregate return becomes materially inferior to the ungated/no-stop
  baseline after identical costs;
- fewer than half of diverse datasets beat SPY and equal-weight benchmarks;
- results depend on one universe or one historical interval;
- conservative stop gaps or realistic friction eliminate viability; or
- a new untouched temporal or point-in-time universe fails to preserve
  competitive return.

## Pipeline Placement

Monthly
[trigger](../stages/OPERATIONS.md#trigger) and static universe are run
configuration. The gated selector controls eligibility and ranking.
Next-session-open entry is strategy-owned. The portfolio policy controls
target, stop, and horizon transitions.
[Funding](../stages/OPERATIONS.md#funding-profiles) and
[evaluation](../stages/OPERATIONS.md#evaluation-plans) remain run
configuration.

## Backtests

- [TC-001: Eight-Dataset Robustness](../backtests/strategies/regime-gated-technical-resistance/tc-001-eight-dataset-robustness.md)
