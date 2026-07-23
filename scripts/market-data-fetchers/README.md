# [Market Data](../../stages/OPERATIONS.md#market-data-resolution) Fetchers

## Stock Price Fetcher

Fetch stock price OHLCV bars and write CSV to stdout. Yahoo Finance is tried first; if it is unavailable or rate-limited, supported intervals fall back to Twelve Data. Set `TWELVEDATA_API_KEY` to use your own key; otherwise the public `demo` key is used.

Naming convention for this folder:

- Scripts are named `fetch_<entity>.py` or `fetch_<entity>_<scope>.py`.
- Data directories use the same entity names, grouped by domain.
- The script name should say what is being fetched, not just that it is historical.

```sh
python3 scripts/market-data-fetchers/fetch_stock_prices.py AAPL 2026-01-01 2026-02-01 1d
```

Date-only end values are inclusive. Datetimes without a timezone are interpreted
as UTC; timezone-aware inputs are normalized to UTC.

The fetcher owns provider [selection](../../stages/OPERATIONS.md#selection-and-selection-models) and normalization. Yahoo Finance and Twelve
Data responses are converted directly to the same canonical row schema; no
provider response archive or replay layer is retained. Canonical CSVs are the
first persisted representation and are the input boundary for downstream
feature generation and future database-ingestion components.

To fetch and merge daily rows into the canonical yearly CSV dataset:

```sh
python3 scripts/market-data-fetchers/backfill_daily_stock_prices.py \
  2026-07-01 2026-07-19
```

By default, the backfill discovers every symbol already present under
`data/stock/prices/daily/`. Use repeated `--symbol` arguments to restrict the
run, `--workers` to change concurrency, or `--prices-dir` to use another
canonical root. Existing and fetched rows are merged by date, sorted, split by
calendar year, and atomically rewritten. For class tickers, the provider symbol
recorded in existing canonical rows is reused while the repository filename is
preserved.

Audit daily coverage without treating pre-listing history or foreign-exchange
holidays as missing SPY sessions:

```sh
python3 scripts/market-data-fetchers/audit_daily_stock_prices.py
```

Use `--output data/stock/prices/daily/.integrity.md` to persist the report. The
audit compares only symbols whose `exchange_timezone` matches the reference
symbol and only between each symbol's first and last valid rows. Other exchange
calendars are reported as unsupported rather than guessed.

Programmatic usage:

```python
from fetch_stock_prices import fetch_historical_csv

csv_text = fetch_historical_csv(
    symbol="AAPL",
    fromDate="2026-01-01",
    toDate="2026-02-01",
    barSize="1d",
)
```

Required output columns are included: `high`, `low`, `open`, `close`, and
`volume`. Additional columns include `symbol`, UTC `datetime`, `date`,
`bar_size`, `adj_close`, `currency`, `exchange_timezone`, and `source`.
The `source` column records the provider used for each row.

Supported `barSize` values are Yahoo Finance intervals: `1m`, `2m`, `5m`,
`15m`, `30m`, `60m`, `90m`, `1h`, `1d`, `5d`, `1wk`, `1mo`, and `3mo`.
Common aliases like `daily`, `weekly`, and `monthly` are also accepted.
Twelve Data fallback is available for `1m`, `5m`, `15m`, `30m`, `1h`, `1d`,
`1wk`, and `1mo`; other valid intervals remain Yahoo-only.

## Analyst Activity Fetcher

Fetch analyst upgrade/downgrade activity and write normalized CSV to stdout.
The default source scrapes public MarketBeat forecast pages and does not require
an API key.

```sh
python3 scripts/market-data-fetchers/fetch_analyst_activity.py AAPL 2026-01-01 2026-07-12
```

Optional Finnhub support is available with `--source finnhub` when
`FINNHUB_API_KEY` is configured.

Required output columns are:

```text
symbol,date,datetime,firm,analyst,from_grade,to_grade,from_price_target,to_price_target,action,source,source_url,fetched_at_utc
```

To fill the repository dataset, use:

```sh
python3 scripts/market-data-fetchers/fill_analyst_activity.py --watchlist watchlists/porter-list.md --start-date 2024-01-01 --end-date 2026-07-12
```

Rows are persisted under `data/stock/analysts/activity/<year>/<ticker>.csv`.
The start and end dates are inclusive. Supply one or more `--watchlist` and/or
`--symbol` arguments; duplicate symbols are collapsed. Existing and fetched
rows are merged, split by year, and atomically rewritten. `--dataset-dir`,
`--workers`, and `--source` override the defaults.

## SEC Quarterly Fundamentals Fetcher

Fetch reported quarterly fundamentals from the SEC Company Facts API:

```sh
SEC_USER_AGENT='Tradix your-email@example.com' \
python3 scripts/market-data-fetchers/fetch_stock_fundamentals.py AAPL \
  --start-date 2014-01-01
```

Persist one or more tickers into the canonical quarterly dataset:

```sh
SEC_USER_AGENT='Tradix your-email@example.com' \
python3 scripts/market-data-fetchers/fill_stock_fundamentals.py \
  --symbol AAPL --symbol MSFT
```

Use `--all-local-symbols` to attempt every ticker in the daily price dataset.
The filler retrieves the SEC ticker map once, fetches one Company Facts document
per eligible ticker, and defaults to a request interval that stays below the
SEC's published 10-request-per-second maximum.

Canonical rows are stored under
`data/stock/fundamentals/quarterly/<available-year>/<ticker>.csv`. The
`available_date` is the SEC filing date, not the fiscal period end. Only
genuinely quarterly duration contexts are accepted; year-to-date and annual
contexts are excluded rather than mislabeled as quarterly observations.
Institutional ownership is not supplied by Company Facts and therefore remains
blank. Set `SEC_USER_AGENT` to an application name and real contact email, as
required by SEC automated-access policy.

## Institutional Holdings Snapshots

Fetch Nasdaq's current ticker-level institutional holdings and aggregate each
holder's reported share change:

```sh
python3 scripts/market-data-fetchers/fetch_stock_institutional_holdings.py AAPL
python3 scripts/market-data-fetchers/fill_stock_institutional_holdings.py \
  --all-local-symbols
```

Snapshots are persisted under
`data/stock/institutions/quarterly/<available-year>/<ticker>.csv`. The
`available_date` is the fetch date. Snapshots are never backdated to the latest
13F report period because holdings become public after the reporting date and
Nasdaq's aggregate may contain managers with different latest report dates.
`net_reported_shares_change` is the sum of the holder-level changes in the
complete response. It is a reported-position accumulation signal, not a claim
about beneficial ownership, short interest, or current intraday holdings.

Historical point-in-time snapshots for configured research universes can be
derived from the SEC's quarterly flattened Form 13F datasets:

```sh
python3 scripts/market-data-fetchers/fill_historical_stock_institutional_holdings.py
```

The historical filler replays filings by actual SEC filing date, aggregates
manager positions per security, and records the sum of each manager's latest
quarter-over-quarter reported share change. Security matching is restricted to
declared issuer aliases; unmatched or ambiguous issuers are reported rather
than guessed.

## Historical S&P 500 Membership

Fetch the pinned and checksummed historical constituent tape with:

```sh
python3 scripts/market-data-fetchers/fetch_historical_sp500_membership.py
```

The result is persisted at
`data/stock/universes/sp500-historical-membership.csv`. See the adjacent
`data/stock/universes/.notes` for provenance, symbol normalization, and the
requirement to report incomplete historical-price coverage separately from
membership coverage.

Attempt recovery of missing 2015–2022 daily prices for historical members with:

```sh
python3 scripts/market-data-fetchers/fill_historical_sp500_prices.py
```

The filler persists only provider histories overlapping each ticker's dated
membership interval and writes an explicit resolved/unresolved report beside
the membership tape.

For symbols no longer served by Yahoo, import the public FNSPID archive after
downloading `Stock_price/full_history.zip`:

```sh
python3 scripts/market-data-fetchers/import_fnspid_historical_sp500_prices.py \
  /path/to/full_history.zip
```

Only unresolved symbols and the repository's required 2014–2022 range are
persisted; the bulk archive remains external temporary data.

Remove invalid imported OHLCV rows without filling gaps:

```sh
python3 scripts/market-data-fetchers/clean_historical_sp500_price_rows.py
```
