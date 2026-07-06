# Stock Price Fetcher

Fetch stock price OHLCV bars and write CSV to stdout. Yahoo Finance is tried first; if it is unavailable or rate-limited, supported intervals fall back to Twelve Data. Set `TWELVEDATA_API_KEY` to use your own key; otherwise the public `demo` key is used.

Naming convention for this folder:

- Scripts are named `fetch_<entity>.py` or `fetch_<entity>_<scope>.py`.
- Data directories use the same entity names, grouped by domain.
- The script name should say what is being fetched, not just that it is historical.

```sh
python3 scripts/market-data-fetchers/fetch_stock_prices.py AAPL 2026-01-01 2026-02-01 1d
```

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
