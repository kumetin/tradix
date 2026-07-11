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

## Strategy, Backtest, and Evaluation Layout

Reusable strategy definitions live under `strategies/`. A strategy file should
describe trading rules, portfolio behavior, data requirements, and strategy
parameters. Do not treat data windows such as `start_date` and `end_date` as
strategy parameters.

Configured strategy instances live under `backtests/`. A backtest file should
select a strategy, reference a concrete universe profile, set strategy
parameters, and explain the edge or hypothesis being tested. Keep schedule,
fallback selection, funding, portfolio-policy, execution, accounting, and
evaluation settings in separate sections instead of labeling all of them as
strategy parameters.

Backtests should compose components in this conceptual order:

```text
strategy
-> schedule
-> universe
-> selection model
-> entry rule
-> portfolio policy
-> execution model
-> funding profile
-> evaluation window
```

Reusable generic inputs should live in their own component directories:
`universes/`, `selection-models/`, `schedules/`, `funding-profiles/`,
`portfolio-policies/`, `execution-models/`, and `evaluations/`. When a backtest
uses one of those generic profiles, reference the profile file instead of
duplicating its values inside the backtest.

Selection models should own ticker eligibility, ranking, target count, target
weights, and fallback behavior. Portfolio policies should own how current
holdings transition toward the selection intent, including whether to sell,
accumulate, rotate, or rebalance. Execution models should own fills, settlement,
fees, slippage, fractional shares, and whether unsettled proceeds can be reused.
Funding profiles should own capital contributions only.

Evaluation windows and train/validation/test split definitions live under
`evaluations/`. Use this layer for full-period tests, holdout periods,
walk-forward schedules, rolling windows, and other validation plans.

Generated backtest or evaluation artifacts should live under
`artifacts/stock/backtests/`, not under `data/`, `strategies/`, `backtests/`,
or `evaluations/`.

Component test specifications live under `tests/`. Prefer behavioral component
tests for `selection-models/`, `portfolio-policies/`, and `execution-models/`.
Use static validation checks for mostly declarative profiles such as
`universes/`, `funding-profiles/`, schedules, evaluations, and backtest link
consistency.

Repository-specific test helper:

- A static validation script exists at `tests/validation/validate_static_profiles.py`.
  - Run it with the repository Python interpreter: `python3 tests/validation/validate_static_profiles.py`.
  - Use this before running higher-level experiments to catch malformed profile files.
  - The codebase contains compiled Python artifacts (`__pycache__/` with cpython-37.pyc),
    so prefer Python 3.7+ when running the included scripts.

Do not create behavioral tests for every static profile by default. Add tests
where the component has logic that can change results silently, such as
look-ahead-prone selection rules, sell/rebalance behavior, or cash settlement
timing.

Research guardrails:

- Enforce point-in-time access. Strategies and selection models must not receive
  full future history when evaluating a past date.
- Distinguish warm-up data from evaluation data. Warm-up rows may initialize
  indicators but must not be included in reported performance metrics.
- Treat current-universe backtests as research tests with current-universe bias
  unless point-in-time constituents are available.
- Preserve locked holdout periods. If a holdout result changes a rule,
  parameter, or component choice, that period is no longer a clean test.
- Record meaningful backtest runs under `experiments/` once an experiment
  registry exists. Do not only preserve winning configurations.
- Benchmark strategy results against `SPY` and, when possible, an equal-weight
  version of the evaluated universe.
- For strategies sourced externally, record provenance under
  `external-strategies/`, freeze the exact specification before testing, and use
  publication date or author data cutoff to define true out-of-sample periods.

## Alerts

Stock alerts and re-entry watchlists live under `alerts/`.

When the user asks to check alerts, review alerts, update alerts, or evaluate
whether watched stocks are worth re-entering:

1. Read `alerts/README.md` first.
2. For `check alerts`, inspect every non-README file under `alerts/`, even if
   the user mentions or links a specific alert file. For other alert requests,
   inspect the relevant alert files under `alerts/`; if the user does not name
   a specific file, inspect all non-README files in that directory.
3. When the user asks to `check alerts`, always evaluate trigger conditions
   against live real-time market data. Use the local daily price and feature
   datasets only as supporting context for moving averages, volume trends,
   historical returns, and setup quality; do not use stale local daily closes as
   the trigger source when live data is available.
4. In `check alerts` responses, group triggered and non-triggered alert rows by
   source alert filename as a subtitle instead of repeating the filename on each
   row.
5. For re-entry watch files, treat the file's `Re-Entry Criteria` section as
   the trigger framework. Classify a watched stock as triggered only when the
   criteria are materially satisfied; otherwise summarize which criteria are
   partial or missing. Do not say there is no trigger merely because there is no
   single explicit price threshold.
6. Treat each alert entry as a sold-stock re-entry watch item. Evaluate it using
   the alert context plus available market data, including:
   - sell price and sell time
   - buy price and buy time
   - relevant support and resistance levels
   - current price versus short-term and long-term moving averages
   - volume trend from the sell date to the current date
   - short-term and long-term volume trends
   - short-term and long-term moving-average trends
7. For any analysis that uses price, moving-average, volume, return, or
   indicator data, also follow the Daily Stock Price Analysis instructions
   above, including reading the `.notes` files before using the daily stock
   dataset.
8. If historical data needed for an alert is absent locally, first populate the
   local daily price dataset using the market data fetcher workflow described
   above. This is required before evaluating the alert. For example, if `IBIT`
   is missing locally, fetch `IBIT`, write the fetched rows into
   `data/stock/prices/daily/<year>/IBIT.csv`, regenerate daily features, and
   then analyze `IBIT` from local `data/stock/features/daily/<year>/IBIT.csv`
   files. Do not analyze the alert directly from a temporary fetched CSV.
9. Give a practical opinion on whether the stock looks worth re-entering, what
   evidence supports or weakens that view, and the approximate watch or holding
   horizon implied by the setup.

Do not present alert analysis as certainty or personalized financial advice.
Make data gaps explicit, especially when an alert lacks buy/sell prices, dates,
support/resistance levels, or current market data.

## Watchlist Setup Reviews

Stock watchlists live under `watchlists/`. Setup evaluation rubrics live under
`setup-evaluators/`.

When the user asks to review a watchlist, rank a watchlist, or evaluate a
watchlist for stock setups:

1. Read `watchlists/README.md` first.
2. Inspect the requested watchlist file. If no file is named and more than one
   watchlist exists, ask which watchlist to review.
3. Read `setup-evaluators/README.md` and
   `setup-evaluators/lower-risk-swing-entry.md`.
4. Use `setup-evaluators/lower-risk-swing-entry.md` for watchlist setup
   reviews.
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
