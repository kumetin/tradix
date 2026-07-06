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

If required historical OHLCV rows are missing from the local daily price
dataset, use the fetchers under `scripts/market-data-fetchers/` before giving up
or asking the user to supply data. Read
`scripts/market-data-fetchers/README.md` first. For stock daily bars, use:

```sh
python3 scripts/market-data-fetchers/fetch_stock_prices.py TICKER START_DATE END_DATE 1d
```

The fetcher writes CSV to stdout and includes `open`, `high`, `low`, `close`,
`adj_close`, and `volume`.

Fetched daily stock data is not considered available for analysis until it has
been persisted into the repository dataset:

```text
data/stock/prices/daily/<year>/<ticker>.csv
```

Split fetched rows by calendar year, create missing yearly ticker files as
needed, and preserve the daily price dataset columns described in
`data/stock/prices/daily/.notes`. Do not rely on CSVs fetched only to `/tmp`,
stdout, or another scratch location for analysis. After adding or updating local
daily price data, regenerate the daily feature files before relying on moving
averages, returns, rolling highs, drawdowns, or volume-derived features.

## Alerts

Stock alerts and re-entry watchlists live under `alerts/`.

When the user asks to check alerts, review alerts, update alerts, or evaluate
whether watched stocks are worth re-entering:

1. Read `alerts/README.md` first.
2. Inspect the relevant alert files under `alerts/`. If the user does not name
   a specific file, inspect all non-README files in that directory.
3. Treat each alert entry as a sold-stock re-entry watch item. Evaluate it using
   the alert context plus available market data, including:
   - sell price and sell time
   - buy price and buy time
   - relevant support and resistance levels
   - current price versus short-term and long-term moving averages
   - volume trend from the sell date to the current date
   - short-term and long-term volume trends
   - short-term and long-term moving-average trends
4. For any analysis that uses price, moving-average, volume, return, or
   indicator data, also follow the Daily Stock Price Analysis instructions
   above, including reading the `.notes` files before using the daily stock
   dataset.
5. If historical data needed for an alert is absent locally, first populate the
   local daily price dataset using the market data fetcher workflow described
   above. This is required before evaluating the alert. For example, if `IBIT`
   is missing locally, fetch `IBIT`, write the fetched rows into
   `data/stock/prices/daily/<year>/IBIT.csv`, regenerate daily features, and
   then analyze `IBIT` from local `data/stock/features/daily/<year>/IBIT.csv`
   files. Do not analyze the alert directly from a temporary fetched CSV.
6. Give a practical opinion on whether the stock looks worth re-entering, what
   evidence supports or weakens that view, and the approximate watch or holding
   horizon implied by the setup.

Do not present alert analysis as certainty or personalized financial advice.
Make data gaps explicit, especially when an alert lacks buy/sell prices, dates,
support/resistance levels, or current market data.

## Watchlist Setup Reviews

Stock watchlists live under `watchlists/`. Setup ranking rubrics live under
`rankers/`.

When the user asks to review a watchlist, rank a watchlist, or evaluate a
watchlist for stock setups:

1. Read `watchlists/README.md` first.
2. Inspect the requested watchlist file. If no file is named and more than one
   watchlist exists, ask which watchlist to review.
3. Read `rankers/README.md` and the selected setup ranker.
4. Use `rankers/lower-risk-swing-entry.md` by default. Use
   `rankers/quantitative-swing-score.md` when the user asks for a quantitative
   score, scorecard, conviction ranking, or setup score. Use
   `rankers/qualitative-pullback-buy-zone.md` only for a lighter qualitative
   pullback or buy-zone review.
5. Parse tickers from the watchlist while preserving category/group headings as
   context.
6. For any analysis that uses price, moving-average, volume, volatility,
   return, RSI, support/resistance, drawdown, or indicator data, also follow
   the Daily Stock Price Analysis instructions above, including reading the
   `.notes` files before using the daily stock dataset.
7. If historical OHLCV data required for the watchlist review is absent
   locally, first populate the local daily price dataset using the market data
   fetcher workflow described above, then regenerate daily features before
   ranking the setup.
8. For analyst targets, analyst counts, rating changes, target revisions,
   estimate revisions, fundamentals, earnings quality, or institutional
   sponsorship signals, use reliable current sources when available. If data is
   unavailable, mark it `N/A`; do not fabricate it.
9. Return a ranked setup table, make data gaps explicit, and do not present the
   result as certainty or personalized financial advice.
