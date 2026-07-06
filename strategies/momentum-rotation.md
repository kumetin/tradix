# Momentum Rotation Strategy

## Strategy Mechanics

This strategy allocates only new cash. Existing holdings are never sold.

At the start of each month, using data available before that month starts, rank the configured universe.

A ticker is eligible if:

```text
(price > long_sma OR medium_sma > long_sma)
AND
drawdown from rolling high > max_drawdown
```

Where:

```text
drawdown = current adjusted close / highest adjusted close in rolling_high_window trading days - 1
```

Among eligible tickers, pick the ticker with the highest trailing return over the configured ranking window.

If no ticker is eligible, use the configured fallback ticker.

## Entry Rule

Once the ticker is selected for the month, do not buy immediately unless the entry setup appears.

Wait for the configured number of consecutive down closes:

```text
close day 1 > close day 2 > ... > close day N
```

When the final down close happens, the setup is known after market close, so the simulated buy happens at the next trading day adjusted open.

If no setup happens during that month, buy at month-end adjusted open. That is the fallback entry.

## Portfolio Behavior

The strategy rotates only for new money. It does not sell old holdings.

For example, if January buys `SOXL`, February buys `XLE`, and March buys `SMCI`, all three positions remain in the portfolio. New monthly cash just goes into the newly selected ticker.

## Parameters

Each parameter set is a separate test case.

| Parameter | Description |
| --- | --- |
| `universe` | Tickers available for monthly ranking and selection. |
| `start_date` | First date included in the backtest period. |
| `end_date` | Last date included in the backtest period. |
| `rebalance_frequency` | How often new cash is allocated and the universe is ranked. |
| `initial_lump_sum` | Cash invested in the first trade month before regular monthly contributions. |
| `monthly_contribution` | Cash added and invested each month. |
| `fractional_shares` | Whether fractional share purchases are allowed. |
| `fees` | Trading fees used by the simulation. |
| `taxes` | Tax assumptions used by the simulation. |
| `slippage` | Slippage assumption used by the simulation. |
| `allow_selling` | Whether existing holdings can be sold. |
| `medium_sma_window` | Medium-term SMA window used in the eligibility rule. |
| `long_sma_window` | Long-term SMA window used in the eligibility rule. |
| `rolling_high_window` | Window used to compute drawdown from recent highs. |
| `max_drawdown` | Minimum allowed drawdown value. A ticker must be above this threshold. |
| `ranking_return_window` | Trailing return window used to rank eligible tickers. |
| `fallback_ticker` | Ticker selected when no ticker passes eligibility. |
| `entry_down_days` | Number of consecutive down closes required before entry. |
| `entry_fallback` | Entry behavior if the down-close setup does not happen during the month. |

## Test Cases

Test cases live under `data/stock/backtests/`.

- [TC-001: High-Beta Universe With SOXL](../data/stock/backtests/momentum-rotation-tc-001-high-beta-with-soxl/README.md)

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
