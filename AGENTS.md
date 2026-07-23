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

## Strategy, Backtest, and [Evaluation](stages/OPERATIONS.md#evaluation-plans) Layout

[Reusable strategy definitions](strategies/README.md) live under `strategies/`.
A strategy file must
state a falsifiable market thesis, proposed mechanism, point-in-time observable
proxies, prediction horizon, required component behavior, thesis-preserving
variations, thesis-changing substitutions, and falsification criteria. A valid
pipeline or arbitrary component combination is not by itself a strategy. Do
not treat data windows such as `start_date` and `end_date` as strategy
parameters.

The [canonical strategy decision pipeline](strategies/README.md#canonical-strategy-decision-pipeline) is
shared by backtests, paper-trading runners, and future live bots. Individual
strategy files describe strategy-owned rules and their pipeline placement.
Concrete stage instances and configuration profiles belong to each configured
runner or backtest;
do not create per-strategy `.flow.md` files that duplicate the canonical
pipeline.

All backtest specifications live under `backtests/`.

Configured strategy backtests live under `backtests/strategies/`. A strategy
backtest file should select a strategy thesis, bind the concrete stages and
configuration required to run it, and set genuine strategy parameters. It is
an executable scenario, not an experiment record: hypotheses, success criteria,
run indexes, results, findings, and decisions belong under `experiments/`.
Scenario files may state configuration intent and their configuration delta
from another scenario, but experiments must reference those scenarios instead
of copying their bindings. Keep
[trigger](stages/OPERATIONS.md#trigger), fallback [selection](stages/OPERATIONS.md#selection-and-selection-models), [funding](stages/OPERATIONS.md#funding-profiles), portfolio-policy, [execution](stages/OPERATIONS.md#execution-and-execution-models), accounting,
and evaluation settings in separate sections instead of labeling all of them as
strategy parameters.

Component-level backtests live under `backtests/components/`. Use this layer
when testing one reusable stage descriptor, such as a [setup evaluator](stages/OPERATIONS.md#setup-evaluators) or
selection model, through its direct input/output contract. A reusable component
must be benchmarkable against itself, a baseline, or another implementation
without running a complete strategy. If a comparison requires a full strategy
harness, it belongs under `backtests/strategies/` as a strategy configuration
comparison.

The [canonical strategy decision pipeline](strategies/README.md#canonical-strategy-decision-pipeline)
distinguishes configuration and services from reusable performance components:

```text
configuration: trigger, static universe, market data
-> selection model
-> optional setup evaluator
-> portfolio policy
-> execution model
run configuration: funding, evaluation plan, benchmarks
```

Reusable stages and their descriptors live under `stages/`, including
`stages/selection-models/`, `stages/portfolio-policies/`,
`stages/execution-models/`, and `stages/setup-evaluators/`. Reusable
configuration inputs live under `configuration/`, including
`configuration/universes/`, `configuration/triggers/`,
`configuration/funding/`, and `configuration/evaluations/`. Reference these files instead of
duplicating their values inside a backtest.

Before creating or changing a reusable stage descriptor, read
`stages/DESCRIPTOR-SCHEMA.md`. Every descriptor must define the common fields,
parameter metadata, and type-specific input/output contract required there.

Triggers, [static universes](stages/OPERATIONS.md#universe-resolution-and-universe-models), funding profiles, evaluation plans, market-data
providers, and benchmark sets are configuration or infrastructure, not reusable
performance stages. Correctness or schema validation does not make a type an
independently benchmarkable component. A dynamic universe qualifies only when
it has a direct point-in-time membership contract and an independently
measurable mandate; expected-return ranking remains selection-model behavior.

Selection models should own ticker eligibility, ranking, target count, target
weights, and fallback behavior. [Portfolio policies](stages/OPERATIONS.md#portfolio-transitions-and-portfolio-policies) should own how current
holdings transition toward the selection intent, including whether to sell,
accumulate, rotate, or rebalance. Execution models should own fills, settlement,
fees, slippage, fractional shares, and whether unsettled proceeds can be reused.
Funding profiles should own capital contributions only.

Evaluation windows and train/validation/test split definitions live under
`configuration/evaluations/`. Use this layer for full-period tests, holdout periods,
walk-forward schedules, rolling windows, and other validation plans.

Generated backtest or evaluation artifacts should live under
`artifacts/stock/backtests/`, not under `data/`, `strategies/`, `backtests/`,
or `configuration/evaluations/`.

Component test specifications live under `tests/`. Prefer behavioral component
tests for `stages/selection-models/`, `stages/portfolio-policies/`, and
`stages/execution-models/`.
Use static validation checks for mostly declarative configuration profiles such as
`configuration/universes/`, `configuration/funding/`, triggers, evaluations,
and backtest link
consistency.

Repository-specific test helper:

- A static validation script exists at `tests/validation/validate_static_profiles.py`.
  - Run it with the repository Python interpreter: `python3 tests/validation/validate_static_profiles.py`.
  - Use this before running higher-level experiments to catch malformed
    descriptors, configuration profiles, and scenario bindings.
  - The codebase contains compiled Python artifacts (`__pycache__/` with cpython-37.pyc),
    so prefer Python 3.7+ when running the included scripts.

Do not create behavioral tests for every static configuration profile by
default. Add tests
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
   against live real-time [market data](stages/OPERATIONS.md#market-data-resolution). Use the local daily price and feature
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
`stages/setup-evaluators/`.

When the user asks to review a watchlist, rank a watchlist, or evaluate a
watchlist for stock setups:

1. Read `watchlists/README.md` first.
2. Inspect the requested watchlist file. If no file is named and more than one
   watchlist exists, ask which watchlist to review.
3. Read `stages/setup-evaluators/README.md` and
   `stages/setup-evaluators/lower-risk-swing-entry.md`.
4. Use `stages/setup-evaluators/lower-risk-swing-entry.md` for watchlist setup
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
