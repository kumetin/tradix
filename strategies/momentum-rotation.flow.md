# Momentum Rotation Flow

This file defines the canonical execution flow for the Momentum Rotation
strategy. Backtests, paper-trading runners, and future live bots should consume
this flow and supply run-mode-specific configuration around it.

## Flow

| Order | Stage | Profile | Responsibility |
| ---: | --- | --- | --- |
| 1 | `trigger` | [Monthly Allocation](../triggers/monthly-allocation.md) | Defines the time, event, or condition rules that cause the strategy to evaluate signals and create allocation opportunities. |
| 2 | `universe` | [High Beta With SOXL](../universes/high-beta-with-soxl.md) | Defines eligible tickers and fallback ticker. |
| 3 | `market_data` | [Daily Stock Features](../data/stock/features/daily/.notes) | Provides point-in-time price and feature rows. |
| 4 | `selection_model` | [SMA Drawdown Trailing Return](../selection-models/sma-drawdown-trailing-return.md) | Ranks eligible tickers and selects the target ticker. |
| 5 | `entry_rule` | [Momentum Rotation Strategy](momentum-rotation.md#entry-rule) | Waits for the configured pullback entry or month-end fallback. |
| 6 | `portfolio_policy` | [New Money Only No Selling](../portfolio-policies/new-money-only-no-selling.md) | Converts selected ticker and available cash into portfolio intent. |
| 7 | `execution_model` | [Frictionless Fractional](../execution-models/frictionless-fractional.md) | Converts portfolio intent into simulated fills. |
| 8 | `funding_profile` | [Initial 5000 Monthly 100](../funding-profiles/initial-5000-monthly-100.md) | Supplies initial and recurring capital for configured runs. |
| 9 | `evaluation_window` | [TC-001 Full Period](../evaluations/momentum-rotation/tc-001-full-period.md) | Defines the historical data window for a configured run. |

## Run Modes

| Run mode | Adds or overrides |
| --- | --- |
| `backtest` | Evaluation window, historical execution assumptions, funding profile, benchmarks, and artifact location. |
| `paper_trading` | Live or delayed market data source, broker account state, order preview behavior, notifications, and paper account safeguards. |
| `live_trading` | Broker account, real order submission, kill switch, market-hours guard, max order sizing, alerting, and incident logging. |

## Notes

The flow order is strategy-owned. Backtests should not redefine the execution
order; they should reference this flow and declare only the profiles or
parameters being tested.

Profiles shown here are the current default harness. Individual backtests may
override a profile, such as the universe or portfolio policy, as part of the
test case.
