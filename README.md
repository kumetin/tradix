# Tradix

Tradix is a local research workspace for stock market data, feature
engineering, and strategy testing.

## What’s in here

- `data/stock/prices/daily/` - raw daily OHLCV price history by year
- `data/stock/features/daily/` - precomputed daily features derived from price
  history
- `scripts/market-data-fetchers/` - helpers for downloading market data
- `scripts/stock-data-enrichment/` - scripts for generating derived datasets
- `strategies/` - strategy notes and backtest specifications
- `watchlists/` - ticker universes to review for trade setups
- `rankers/` - reusable setup ranking rubrics for watchlist reviews

## Current Strategy Note

The active strategy being tested is documented here:

- [`strategies/momentum-rotation.md`](strategies/momentum-rotation.md)

It describes a monthly momentum rotation model with:

- a fixed high-beta universe
- new-money-only allocation
- no selling of prior positions
- a 4-down entry setup or month-end fallback

## Data Notes

Before analyzing daily stock data or calculating indicators such as moving
averages, RSI, volatility, or returns, read:

- `data/stock/prices/daily/.notes`
- `data/stock/features/daily/.notes`

Those notes cover ticker-history gaps, class ticker naming, and blank OHLCV
rows.

## IBKR Flex Portfolio Analysis

If you are analyzing an Interactive Brokers Flex portfolio, use:

```sh
scripts/ibkr-flex-query.sh ACCOUNT_ID portfolio
```

Local configuration is expected in:

- `~/.ibkr/flex-queries.csv`
- `~/.ibkr/flex-tokens.csv`

See `AGENTS.md` for the workflow.

## Watchlist Reviews

Watchlists define ticker universes, while prompt files define the setup ranking
rubrics used to evaluate them. For example:

- [`watchlists/ai-infrastructure.md`](watchlists/ai-infrastructure.md)
- [`rankers/lower-risk-swing-entry.md`](rankers/lower-risk-swing-entry.md)

See `watchlists/README.md`, `rankers/README.md`, and `AGENTS.md` for the
review workflow.
