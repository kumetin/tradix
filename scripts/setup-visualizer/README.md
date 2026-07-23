# Setup Visualizer

Render one lower-risk swing-entry setup row as an SVG chart using local daily
stock feature data.

The visualizer is intended for rows produced by:

- `watchlists/README.md`

It plots adjusted daily close, the entry zone, buy limit, stop loss or
invalidation level, take-profit level, key support and resistance levels,
mentioned SMA lines, and SMA150.

Default usage:

```sh
python3 scripts/setup-visualizer/setup_visualizer.py --setup-line '| 1 | NVDA | $210.96 | ... |'
```

Pipe a row from a file:

```sh
python3 scripts/setup-visualizer/setup_visualizer.py < /tmp/setup-row.md
```

Write to a specific SVG path:

```sh
python3 scripts/setup-visualizer/setup_visualizer.py \
  --setup-line '| 1 | NVDA | $210.96 | ... |' \
  --output /tmp/nvda-setup.svg
```

The default chart period is 252 daily bars. Local price data is daily-only, and
one year gives enough context for support, resistance, trend, and SMA150 without
hiding the entry setup in too much history.

Primary input:

- `data/stock/features/daily/<year>/<symbol>.csv`

Primary output:

- `artifacts/stock/setup-visualizations/`

Current script:

- `setup_visualizer.py`
