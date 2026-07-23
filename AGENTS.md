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

### IBKR Flex Trade History

When a review needs executed buy or sell information, including a FOMO-list
review, use the configured `trades` Flex query instead of relying only on
handwritten prices:

1. Discover accounts in `~/.ibkr/flex-tokens.csv`.
2. Cross-check `~/.ibkr/flex-queries.csv` for a `trades` query.
3. If multiple eligible accounts exist and the intended account cannot be
   resolved from context, ask which account to use.
4. Run:

   ```sh
   scripts/ibkr-flex-query.sh ACCOUNT_ID trades
   ```

5. Parse the CSV by header name. For sales, require `Buy/Sell=SELL`; use
   `Symbol`, `DateTime`, `TradeDate`, `Quantity`, `TradePrice`,
   `FifoPnlRealized`, `TradeID`, `IBOrderID`, and `TransactionID` as available.

For a FOMO entry, match the ticker and the recorded sale date when the alert
provides one. If one liquidation was executed in multiple fills, calculate the
absolute-quantity-weighted average `TradePrice` across fills belonging to the
same sale event and report the total sold quantity. Keep distinct sales on
different dates separate. When the alert refers to one sale without enough
detail to distinguish multiple candidates, use the most recent loss-realizing
closing sale and explicitly identify the chosen date. Never average unrelated
sale events.

Use `FifoPnlRealized` to confirm that a FOMO sale was loss-realizing. Treat the
execution price as the sell price; commissions may be reported separately and
must not be silently folded into `TradePrice`. Do not expose Flex tokens or
unrelated trades.

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

The user calls `alerts/cut-loss-re-entry-watch.md` the **FOMO list** or
**FOMO watchlist**. It is the list of stocks sold at a loss that the user wants
to monitor for a recovery so a potential re-entry is not missed. A request to
review the FOMO list means to review that file as a sold-stock re-entry
watchlist and print the `Forcast Table` defined below. Pull its executed sales
from the IBKR Flex `trades` query using the Trade History workflow above.

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

## Forcast Table

Whenever the user asks to review a watchlist, portfolio, or arbitrary list of
stocks, print one consolidated table named `Forcast Table`. Preserve this
spelling.

### Bookmarkable recurring review pages

At the beginning of each new working session in this repository, refresh the
portfolio, FOMO watchlist, AI Infrastructure watchlist, and Porter watchlist
reviews in the background as soon as tool use is appropriate. Follow every
data-source, persistence, point-in-time, and presentation rule in this file.
Write the resulting HTML pages to these constant bookmark targets, overwriting
the prior generated review rather than putting a date in the filename:

```text
artifacts/stock/bookmarks/portfolio.html
artifacts/stock/bookmarks/fomo.html
artifacts/stock/bookmarks/ai-infrastructure.html
artifacts/stock/bookmarks/porter.html
```

Show the calculation date in parentheses immediately to the right of the major
page title, for example `Portfolio Review (2026-07-23)`. Always include the
calculation date in every watchlist table page title. Keep the filename and
bookmark path constant across refreshes.

Also start or resume the slow TipRanks analyst-data collection queue at the
beginning of every working session in this repository. The queue covers the
union of all tickers mentioned in every file under `watchlists/`, runs at a
conservative rate, and continues past per-ticker failures. For each ticker,
scrape the complete set of analyst iterations exposed on the entire forecast
page, not merely the first card or the 30-day subset, and persist the normalized
summary and activity records under the TipRanks data directories defined below.
Make the collector resumable so already-completed same-day tickers are skipped.
On a later collection date, read the forecast-page analyst iterations from the
top in displayed newest-to-oldest order. Persist the new leading rows and stop
at the first activity row that already exists in the ticker's persisted
activity CSV; do not continue scanning or rewriting older known history.
If local HTTP or browser automation is blocked, retain the failure in the queue
for the required external-browser fallback; never write fabricated or partial
success data.

### Preparation

For watchlists, follow the Watchlist Setup Reviews workflow above and use
`stages/setup-evaluators/lower-risk-swing-entry.md` to determine setup quality.
For current portfolios, follow the IBKR Flex Portfolio Analysis workflow above.
For price- or indicator-based columns, follow the Daily Stock Price Analysis
workflow above, including reading both daily-data `.notes` files and persisting
and enriching any missing history before analysis.

Use the latest completed trading day as the common decision cutoff. Every
technical and ranking measurement must use only information available by that
cutoff. Preserve watchlist categories as evaluation context. If data is
unavailable or a metric is invalid, print `N/A` rather than estimating or
fabricating it.

### Exact column order

Print columns in this exact left-to-right order:

1. `Ticker`
2. `Last 1W`
3. `Last 2W`
4. `Technical Condition`
5. `Continuation View`
6. For FOMO-list reviews only: `Sell Price`
7. For portfolio reviews only: `Average Buy Price`
8. For portfolio reviews only: `Current Price`
9. For portfolio reviews only: `Unrealized P/L %`
10. For portfolio reviews only: `Unrealized P/L`
11. `Setup Rank`
12. `Momentum Rank`
13. `12-1 Momentum %`
14. `Last 1M`
15. `ATR-14`
16. `Analyst Upside %`
17. `Analysts Last 30d`
18. `Distance from High %`
19. `P/E vs own 5Y avg %`
20. `P/E vs Sector %`

Sort rows by `Setup Rank`, best setup first. Keep `Setup Rank` immediately left
of `Momentum Rank`, and keep `Last 1M` immediately right of
`12-1 Momentum %`.

For portfolio reviews, insert the four portfolio-only columns together,
immediately after `Continuation View`, in exactly this order:
`Average Buy Price`, `Current Price`, `Unrealized P/L %`, `Unrealized P/L`.
Take them from the current IBKR Flex portfolio output. Calculate unrealized
percentage as `(Current Price / Average Buy Price - 1) * 100` when both values
are usable; use the Flex `FifoPnlUnrealized` value for `Unrealized P/L`.

For FOMO-list reviews, insert `Sell Price` immediately after
`Continuation View`. Retrieve it from the matched IBKR Flex execution rather
than relying only on the alert text. Render the execution price and sale date
together, for example `$135.45 (2026-07-06)`. When a sale had multiple fills,
use the same-event quantity-weighted price defined in the Trade History
workflow.

### Column definitions and sources

- `Ticker`: Use the normalized exchange ticker and preserve class-share
  conventions documented in the local daily-data notes.
- `Last 1W`: Adjusted-close return over five trading sessions:
  `(latest adjusted close / adjusted close 5 sessions earlier - 1) * 100`.
- `Last 2W`: Adjusted-close return over ten trading sessions:
  `(latest adjusted close / adjusted close 10 sessions earlier - 1) * 100`.
- `Technical Condition`: Give a concise factual description based on current
  adjusted price; the level and direction of the 20-day and 50-day SMAs; recent
  support and resistance; short-term volume behavior; and whether price is
  extended from or reclaiming those averages. Do not use analyst opinions for
  this column.
- `Continuation View`: Give a concise evidence-based view of continuation
  quality over approximately the next one to two weeks. Consider one-week and
  two-week returns, moving-average position and direction, ATR and price
  extension, recent volume confirmation, pullback depth, support and
  resistance, momentum rank, absolute momentum, and exhaustion or
  mean-reversion risk.
- `Setup Rank`: Rank only the displayed stocks as `1/N` through `N/N`, using
  `stages/setup-evaluators/lower-risk-swing-entry.md`. This measures current
  entry/setup quality and must not duplicate Momentum Rank. Prefer constructive
  structure, nearby support, favorable reward relative to downside, improving
  moving averages, confirming volume, manageable ATR/extension, and
  continuation without obvious exhaustion. Penalize excessive extension,
  broken support, declining short-term averages, unconfirmed rebounds, high
  volatility without defined risk, and poor reward-to-risk.
- `Momentum Rank`: Calculate Classic 12-1 Momentum across the complete
  applicable comparison universe, not merely the displayed subset. Format as
  `rank/eligible-universe-count`; lower is stronger. For watchlists, use the
  complete resolved watchlist universe specified by the applicable ranking
  analysis. For a portfolio or arbitrary list, explicitly state the comparison
  universe. Never silently mix ranks from incompatible universes.
- `12-1 Momentum %`: Calculate
  `(adjusted close approximately 21 trading sessions before cutoff / adjusted
  close approximately 252 trading sessions before cutoff - 1) * 100`.
  Operationally, for an ordered series including the cutoff row, use
  `(adj_close[-22] / adj_close[-253] - 1) * 100`. This skips the most recent
  month and measures the preceding approximately eleven months. Enforce
  point-in-time access and exclude symbols without enough history.
- `Last 1M`: Adjusted-close return over approximately 21 trading sessions:
  `(latest adjusted close / adjusted close 21 sessions earlier - 1) * 100`.
- `ATR-14`: Calculate 14-session Average True Range from adjusted OHLC data.
  For each session, true range is the maximum of adjusted high minus adjusted
  low, the absolute difference between adjusted high and previous adjusted
  close, and the absolute difference between adjusted low and previous adjusted
  close. Use one standard 14-period ATR implementation consistently. Display
  both currency ATR and percentage of current adjusted price as
  `$ATR / ATR%`, for example `$78.25 / 8.62%`.
- `Analyst Upside %`: Scrape the current average 12-month price target and
  displayed upside/downside from
  `https://www.tipranks.com/stocks/<lowercase-ticker>/forecast`. Link the
  displayed percentage to that page. Preserve TipRanks' displayed percentage
  because its cached reference price can differ from the local close. Use
  `N/A` when there is no usable consensus.
- `Analysts Last 30d`: Count distinct human analysts in TipRanks' `Detailed
  List of Analyst Forecasts` whose displayed action date falls in the inclusive
  30-calendar-day window ending on the collection date. Include dated
  initiations, assignments, reiterations, upgrades, downgrades, and
  price-target changes. Count an analyst only once even if they have multiple
  actions. Do not use TipRanks' headline count, which covers three months. Do
  not count entries outside the window or undated entries. If detailed entries
  are hidden or cannot be verified, print `N/A`. Record the collection date.
- `Distance from High %`: Use the highest valid adjusted daily high in all
  available history through the cutoff and calculate
  `(latest adjusted close / all-time adjusted high - 1) * 100`. This is
  distance from the all-time high, not the 52-week high. Never use a future high
  in a historical review.
- `P/E vs own 5Y avg %`: Use current trailing P/E and the stock's five-year
  average trailing P/E from a current, identifiable source such as
  FinanceCharts. Calculate
  `(current trailing P/E / own five-year average trailing P/E - 1) * 100`.
  Print `N/A` for negative or non-meaningful earnings/P/E, insufficient
  history, or an unavailable five-year average. Never percentage-compare a
  negative P/E.
- `P/E vs Sector %`: Use current trailing P/E and a current sector P/E
  benchmark from a consistent, identifiable source and classification system.
  Calculate `(current trailing P/E / sector benchmark P/E - 1) * 100`. Prefer a
  sector median because P/E distributions are skewed, and disclose below the
  table when a median is used. Do not mix sector and industry classifications
  or forward and trailing P/E benchmarks. Print `N/A` for a negative or
  non-meaningful current P/E.

### Persistent TipRanks analyst data

Whenever TipRanks analyst data is scraped for any task, persist the normalized
results before presenting them. Store summary observations under
`data/stock/tipranks-analysts-summary/` and individual analyst activity under
`data/stock/tipranks-analysts-activity/`, partitioned into one
`<TICKER>.csv` file per ticker in each directory. Read each directory's
`.notes` before writing.

The summary CSV schema is:

```text
scrape_date,ticker,average_rating_90d,average_forecast_price_90d,average_forecast_upside_90d,average_upside_30d,average_rating_30d
```

For the three 90-day fields, scrape the consensus rating, average 12-month
forecast price, and displayed average forecast upside from the top of the
TipRanks forecast page. Do not substitute values calculated from the detailed
rows for those fields. Normalize the displayed consensus rating before
persistence using `Strong Buy = 5`, `Moderate Buy = 4`, `Hold = 3`,
`Moderate Sell = 2`, and `Strong Sell = 1`. Leave unrecognized or unavailable
ratings blank; do not persist the categorical label in `average_rating_90d`.

The activity CSV schema is:

```text
activity_date,ticker,analyst_name,analyst_grade_1_to_5,expert_firm,price_target,position,upside_downside,action
```

Scrape every available analyst iteration, preserving the displayed activity
date, analyst name, TipRanks analyst grade on its 1-to-5 scale, firm, price
target, position, upside/downside, and action. Do not infer a missing analyst
grade from the position or action.

Calculate the two 30-day summary fields from the persisted detailed rows in the
inclusive 30-calendar-day window ending on `scrape_date`:

- `average_upside_30d` is the arithmetic mean of numeric
  `upside_downside` observations in the window.
- `average_rating_30d` is the arithmetic mean of numeric
  `analyst_grade_1_to_5` observations in the window.

Deduplicate activity rows by all schema fields so rerunning a scrape does not
append identical observations. Upsert summary rows by `scrape_date,ticker`.
Use the repository TipRanks fetcher when it works. If TipRanks blocks local
automation or omits required rendered data, retrieve the page through the
available external browsing path, normalize the same fields, persist them to
the same CSVs, and make the fallback explicit. Never fabricate hidden fields;
leave unavailable values blank and explain material gaps.

### ETF TipRanks analyst rating and forecast

When an ETF needs an analyst rating or forecast, resolve it in this order:

1. Check `data/stock/tipranks-analysts-summary/<ETF>.csv`. If it contains a
   row for the calculation date with usable direct ETF consensus data, use
   that observation and do not synthesize a constituent-weighted result.
2. Otherwise, check `data/etf/holdings/<ETF>-holdings.csv` for a holdings
   observation on the calculation date. Read
   `data/etf/holdings/.notes` before reading or writing this dataset.
3. If there is no same-day holdings observation, retrieve the ETF's current
   holdings from an identifiable web source. Select the largest holdings in
   descending portfolio-weight order until their cumulative weight is at
   least 80% of ETF capital. Persist the same-day holdings observation before
   calculating the ETF result.
4. For every selected constituent, first reuse a same-day observation from
   `data/stock/tipranks-analysts-summary/<TICKER>.csv` when available.
   Otherwise use the external browsing path to scrape the latest TipRanks
   consensus and all detailed analyst activity needed for the inclusive
   30-calendar-day window. Do not attempt TipRanks HTTP or headless-browser
   requests from the local machine. Persist normalized activity and summary
   data according to the Persistent TipRanks analyst data rules above before
   using it in the ETF calculation.
5. Read the newest constituent summary row on or before the calculation date.
   Calculate each ETF-level analyst field as a holding-weighted mean over
   constituents with a usable numeric value for that field. Re-normalize by
   the sum of included weights separately for each field; do not treat missing
   values as zero. Report both selected-holdings coverage and usable-weight
   coverage as material data-quality context.
6. Upsert the resulting ETF observation into
   `data/etf/tipranks-analysts-summary/<ETF>.csv`. Read that directory's
   `.notes` before writing.

The ETF summary schema is:

```text
date,ticker,average_rating_90d,average_forecast_price_90d,average_forecast_upside_90d,average_upside_30d,average_rating_30d
```

The ETF-level forecast price is a weighted mean of constituent price targets
and is not a price target in the ETF's own share-price units. Label it as a
constituent-weighted diagnostic whenever it is presented. Prefer the weighted
upside and rating fields for comparisons between ETFs. Calculate the weighted
90-day rating from the normalized numeric values (`Strong Buy = 5` through
`Strong Sell = 1`) and leave it blank when no constituent has a usable value.

#### Leveraged ETF TipRanks analyst rating and forecast

For a leveraged or inverse ETF, use this resolution branch before running the
ordinary constituent workflow:

1. Check `data/stock/tipranks-analysts-summary/<LEVERAGED_ETF>.csv`. If it has
   a usable direct TipRanks observation for the calculation date, use it
   unchanged.
2. Otherwise resolve and verify the product's base ETF and stated daily
   leverage factor from `data/etf/leveraged-etf-mappings.csv`. Read
   `data/etf/.notes` before using or updating the mapping. A negative factor
   denotes inverse exposure.
3. Check both
   `data/stock/tipranks-analysts-summary/<BASE_ETF>.csv` and
   `data/etf/tipranks-analysts-summary/<BASE_ETF>.csv` for a same-day
   observation, preferring a direct stock-directory observation over a
   constituent-derived ETF observation.
4. If neither contains a same-day base-ETF observation, run the ordinary ETF
   TipRanks workflow above for the base ETF. Once it completes, read the
   persisted base-ETF observation; do not calculate from unpersisted values.
5. Derive and upsert the leveraged ETF row in
   `data/etf/tipranks-analysts-summary/<LEVERAGED_ETF>.csv`.

Apply leverage only to return-like forecast fields:

- `average_forecast_upside_90d = base average_forecast_upside_90d * leverage_factor`
- `average_upside_30d = base average_upside_30d * leverage_factor`

Do not multiply categorical or ordinal rating fields by leverage. Copy
`average_rating_90d` and `average_rating_30d` from the base ETF as directional
analyst-sentiment context and label them as inherited, not direct leveraged-ETF
ratings.

Never multiply the base ETF's dollar forecast price by the leverage factor;
the base and leveraged funds have different share-price units, and daily reset
and compounding make that result invalid. When a current leveraged-ETF price is
available for the same cutoff, derive an explicitly synthetic price diagnostic
as:

```text
leveraged_forecast_price =
    current_leveraged_etf_price * (1 + leveraged_forecast_upside_90d / 100)
```

Otherwise leave `average_forecast_price_90d` blank. Label every derived row as
a leverage-scaled diagnostic, not a direct analyst target, and disclose that
daily reset, volatility drag, fees, tracking error, and forecast-horizon
mismatch can make realized multi-day returns differ materially from the simple
factor-scaled result.

### Persistent P/E valuation data

Whenever P/E data is retrieved for any task, persist the normalized observation
before presenting it. Store observations under
`data/stock/pe-valuation-summary/`, partitioned into `<year>.csv` by
`scrape_date`, and read that directory's `.notes` before writing.

The CSV schema is:

```text
scrape_date,ticker,source_as_of_date,current_trailing_pe,own_5y_average_pe,own_5y_distance_pct,sector_name,sector_benchmark_method,sector_benchmark_pe,sector_distance_pct,source_url,sector_source_url
```

Use trailing P/E consistently. Preserve the source's own as-of date separately
from the scrape date. Calculate distance fields as
`(current trailing P/E / benchmark P/E - 1) * 100`. Record whether the sector
benchmark is a mean or median and do not mix forward P/E with trailing P/E.
Upsert observations by `scrape_date,ticker`. If current earnings or P/E are
negative or non-meaningful, or if a benchmark cannot be verified, leave the
affected fields blank rather than manufacturing a comparison. Record the
direct source URLs and make source-date or methodology mismatches explicit.

### Presentation

Show returns and valuation distances with explicit `+` or `-` signs and two
decimal places. Link `Analyst Upside %` to TipRanks. Immediately below the
table, state the decision cutoff, analyst-scrape date, Momentum Rank comparison
universe, and sector-benchmark methodology. Make material data gaps explicit.
Render the table at full logical width: do not combine or omit columns merely
to fit the viewport. Use a horizontally scrollable HTML container and an HTML
table with a large explicit `min-width`. Keep `Ticker` and other identity cells
on one line. `Technical Condition` and `Continuation View` are exceptions:
keep their wording concise, allow them to wrap, and give them narrower fixed or
maximum widths so they do not dominate the table. Do not use Markdown table
auto-layout for a wide Forcast Table when it causes other columns to shrink.
The user prefers the bottom horizontal scrollbar over squeezed columns.
Do not present the output as certainty or personalized financial advice.
