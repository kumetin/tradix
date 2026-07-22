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
high. Rows without both `close` and `adj_close` are skipped rather than
forward-filled. The script also regenerates the feature dataset `.notes` file.
