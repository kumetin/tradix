# Momentum Rotation Strategy

Strategy flow: [Momentum Rotation Flow](momentum-rotation.flow.md)

## Strategy Mechanics

At each triggered ranking date, using only data available before that date, run
the configured selection model against the configured universe.

The selection model returns one target ticker. This strategy then waits for the
configured entry rule before producing an executable order for the portfolio
policy.

The current backtests use the
[SMA Drawdown Trailing Return](../selection-models/sma-drawdown-trailing-return.md)
selection model.

## Entry Rule

Once the ticker is selected for the month, do not buy immediately unless the entry setup appears.

Wait for the configured number of consecutive down closes:

```text
close day 1 > close day 2 > ... > close day N
```

When the final down close happens, the setup is known after market close, so the simulated buy happens at the next trading day adjusted open.

If no setup happens during that month, buy at month-end adjusted open. That is the fallback entry.

## Portfolio Policy Compatibility

The strategy produces a selected ticker for each triggered allocation date. The
portfolio policy decides how that selection affects holdings.

Different backtests may run this strategy with different portfolio policies. A
new-money-only policy accumulates every prior selection, while a rotation policy
sells the current holding when a different ticker is selected and the new buy
order is executed.

## Strategy Parameters

These parameters define the reusable strategy entry logic.

| Parameter | Description |
| --- | --- |
| `entry_down_days` | Number of consecutive down closes required before entry. |
| `entry_fallback` | Entry behavior if the down-close setup does not happen during the month. |

## External Inputs and Platform Layers

These settings are required to run the strategy, but they are owned by other
parts of the platform.

| Setting | Owner | Description |
| --- | --- | --- |
| `universe` | `universes/` | Tickers available for monthly ranking and selection. |
| `fallback_ticker` | `universes/` | Ticker selected when no ticker passes eligibility. |
| Ticker selection logic | `selection-models/` | Eligibility filters, ranking rules, and fallback behavior used to choose the target ticker. |
| `trigger_frequency` | `triggers/` | How often the strategy evaluates signals and creates allocation opportunities. |
| `initial_lump_sum` | `funding-profiles/` | Cash available in the first trade month before regular monthly contributions. |
| `monthly_contribution` | `funding-profiles/` | Cash added on each contribution date. |
| `allow_selling` | `portfolio-policies/` | Whether existing holdings can be sold. |
| `fractional_shares` | `execution-models/` | Whether fractional share purchases are allowed. |
| `fees` | `execution-models/` | Trading fees used by the simulation. |
| `taxes` | `execution-models/` | Tax assumptions used by the simulation. |
| `slippage` | `execution-models/` | Slippage assumption used by the simulation. |
| `start_date` / `end_date` | `evaluations/` | Historical data window used for a run or split. |
| Train/validation/test splits | `evaluations/` | Full-period, holdout, rolling, or walk-forward validation plan. |

## Backtests

Configured backtest instances live under `backtests/strategies/momentum-rotation/`.
Generated backtest artifacts should live under `artifacts/stock/backtests/`.
Evaluation windows and data splits live under `evaluations/`.

- [TC-001: High-Beta Universe With SOXL](../backtests/strategies/momentum-rotation/tc-001-high-beta-with-soxl.md)
- [TC-002: Random Universe](../backtests/strategies/momentum-rotation/tc-002-random-universe.md)
- [TC-003: Random Universe Multi-Position Initial Only](../backtests/strategies/momentum-rotation/tc-003-random-universe-multi-position-initial-only.md)

## Data Used

Raw prices:

```text
data/stock/prices/daily/<year>/<ticker>.csv
```

Precomputed features:

```text
data/stock/features/daily/<year>/<ticker>.csv
```

Features include adjusted open/high/low, `SMA20`/`SMA50`/`SMA100`/`SMA150`/`SMA200`, trailing returns, rolling highs, and drawdowns.
