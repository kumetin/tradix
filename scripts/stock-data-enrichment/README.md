# Stock Data Enrichment

This folder holds scripts that derive additional local datasets from already
stored stock data. It does not contain raw-data fetchers.

Primary output:

- `data/stock/features/...`

Current script:

- `precompute_daily_stock_features.py`

Run it from the repository root to rebuild every available symbol:

```sh
python3 scripts/stock-data-enrichment/precompute_daily_stock_features.py
```

Limit a rebuild to one or more symbols with repeated `--symbol` arguments:

```sh
python3 scripts/stock-data-enrichment/precompute_daily_stock_features.py \
  --symbol AAPL \
  --symbol SPY
```

`--prices-dir` and `--features-dir` override the default input and output roots.
The script reads each symbol across all available years, computes features over
that continuous history, and then splits output rows back into yearly files.

Generated fields include adjusted open/high/low, SMA 20/50/100/150/200,
21/63/126/252-trading-row returns, the 252-row high, and drawdown from that
high. It also derives the requested boolean trend fields from dated quarterly
facts in `data/stock/fundamentals/quarterly/`, plus price-above-SMA-200 and
252-row return above SPY. Fundamental rows are applied from `available_date`,
never from the fiscal period end. Growth, margin, revenue, and debt compare the
latest reported quarter with its closest comparable year-ago quarter; missing
evidence produces a blank value. Institutional accumulation comes from dated
snapshots in `data/stock/institutions/quarterly/` and is true when the aggregate
reported institutional share change is positive.
The technical output also includes 50-row relative volume. High relative
volume is true only when the adjusted close rises from the previous valid row
and current volume is at least 1.5 times the mean of the prior 50 valid rows;
the current row is excluded from that average.
Rows without both `close` and `adj_close` are skipped rather than
forward-filled. The script also regenerates the feature dataset `.notes` file.
