## IBKR Flex Portfolio Analysis

This repository includes an Interactive Brokers Flex Web Service helper at
`scripts/ibkr-flex-query.sh`.

When the user asks to analyze their current portfolio, use this helper instead
of asking the user to manually export portfolio data.

Expected local configuration:

- `~/.ibkr/flex-queries.csv`
  - CSV columns: `account_id,query_name,query_id`
- `~/.ibkr/flex-tokens.csv`
  - CSV columns: `account_id,query_token`

Workflow for portfolio analysis:

1. Discover available accounts by reading `~/.ibkr/flex-tokens.csv`.
2. Cross-check those accounts against `~/.ibkr/flex-queries.csv` for a
   `portfolio` query.
3. If more than one account is available, show the user a menu of eligible
   account IDs and ask which account to analyze.
4. Run:

   ```sh
   scripts/ibkr-flex-query.sh ACCOUNT_ID portfolio
   ```

5. Treat the command output as the current portfolio state in CSV format and
   analyze it.

Do not print, expose, or ask the user to paste Flex tokens. Use the token only
through the local helper script and local configuration files.

## Daily Stock Price Analysis

Daily stock price CSVs are stored under `data/stock/prices/daily/<year>/`.
Precomputed daily feature CSVs are stored under
`data/stock/features/daily/<year>/`.

Before analyzing this dataset or calculating indicators such as moving
averages, RSI, volatility, or returns, read:

```sh
data/stock/prices/daily/.notes
data/stock/features/daily/.notes
```

Use those notes to account for shorter ticker histories, missing trading-day
rows, class ticker filename conventions, and known blank OHLCV rows. Do not
assume every ticker has a complete 1254-row history, and do not forward-fill
missing OHLCV data unless the user explicitly requests it.

For analyses that need adjusted open/high/low, moving averages, trailing
returns, rolling highs, or drawdowns, prefer the precomputed feature files when
available. Regenerate them with:

```sh
scripts/stock-data-enrichment/precompute_daily_stock_features.py
```
