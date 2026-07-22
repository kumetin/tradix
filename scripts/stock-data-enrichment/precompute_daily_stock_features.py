#!/usr/bin/env python3
"""Precompute daily technical features from yearly OHLCV price CSVs.

Parameters:
    ``--prices-dir`` selects canonical input, ``--features-dir`` selects output,
    and repeatable ``--symbol`` values restrict processing.
External sources:
    Local yearly canonical price CSVs only; no network service is accessed.
Side effects:
    Creates feature year directories, replaces generated per-symbol CSVs, and
    writes the feature dataset ``.notes`` file.
Examples:
    Recompute features for the full local dataset::

        python3 scripts/stock-data-enrichment/precompute_daily_stock_features.py

    Recompute only selected symbols into a separate tree::

        python3 scripts/stock-data-enrichment/precompute_daily_stock_features.py --symbol AAPL --symbol MSFT --features-dir /tmp/features
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict, deque
from pathlib import Path


DEFAULT_SMA_WINDOWS = (20, 50, 100, 150, 200)
DEFAULT_RETURN_WINDOWS = (21, 63, 126, 252)
DEFAULT_HIGH_WINDOWS = (252,)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Precompute daily features into data/stock/features/daily/<year>/<symbol>.csv"
    )
    parser.add_argument(
        "--prices-dir",
        type=Path,
        default=Path("data/stock/prices/daily"),
        help="Input yearly price directory.",
    )
    parser.add_argument(
        "--features-dir",
        type=Path,
        default=Path("data/stock/features/daily"),
        help="Output yearly feature directory.",
    )
    parser.add_argument(
        "--symbol",
        action="append",
        dest="symbols",
        help="Only process this symbol. Can be passed more than once.",
    )
    return parser.parse_args()


def read_symbol_rows(prices_dir: Path) -> dict[str, list[dict[str, str]]]:
    rows_by_symbol: dict[str, list[dict[str, str]]] = defaultdict(list)
    for csv_path in sorted(prices_dir.glob("*/*.csv")):
        if csv_path.parent.name.startswith("."):
            continue
        with csv_path.open(newline="") as handle:
            for row in csv.DictReader(handle):
                symbol = row.get("symbol") or csv_path.stem
                if not row.get("date"):
                    continue
                rows_by_symbol[symbol].append(row)

    for rows in rows_by_symbol.values():
        rows.sort(key=lambda row: row["date"])
    return rows_by_symbol


def as_float(row: dict[str, str], column: str) -> float | None:
    value = row.get(column)
    if value in (None, ""):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def fmt(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.10f}".rstrip("0").rstrip(".")


class RollingHigh:
    def __init__(self, window: int) -> None:
        self.window = window
        self.values: deque[tuple[int, float]] = deque()

    def push(self, index: int, value: float) -> None:
        while self.values and self.values[-1][1] <= value:
            self.values.pop()
        self.values.append((index, value))
        min_index = index - self.window + 1
        while self.values and self.values[0][0] < min_index:
            self.values.popleft()

    def current(self, index: int) -> float | None:
        if index + 1 < self.window or not self.values:
            return None
        return self.values[0][1]


def feature_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    sums = {window: 0.0 for window in DEFAULT_SMA_WINDOWS}
    queues = {window: deque() for window in DEFAULT_SMA_WINDOWS}
    rolling_highs = {window: RollingHigh(window) for window in DEFAULT_HIGH_WINDOWS}
    adj_closes: list[float] = []
    output: list[dict[str, str]] = []

    for index, row in enumerate(rows):
        close = as_float(row, "close")
        adj_close = as_float(row, "adj_close")
        open_price = as_float(row, "open")
        high = as_float(row, "high")
        low = as_float(row, "low")

        if close is None or adj_close is None:
            continue

        adj_factor = adj_close / close if close else 1.0
        adj_open = open_price * adj_factor if open_price is not None else None
        adj_high = high * adj_factor if high is not None else None
        adj_low = low * adj_factor if low is not None else None

        adj_closes.append(adj_close)
        for window in DEFAULT_SMA_WINDOWS:
            queues[window].append(adj_close)
            sums[window] += adj_close
            if len(queues[window]) > window:
                sums[window] -= queues[window].popleft()

        for high_window in rolling_highs.values():
            high_window.push(index, adj_close)

        feature = {
            "symbol": row.get("symbol", ""),
            "date": row["date"],
            "bar_size": row.get("bar_size", ""),
            "open": row.get("open", ""),
            "high": row.get("high", ""),
            "low": row.get("low", ""),
            "close": row.get("close", ""),
            "adj_close": row.get("adj_close", ""),
            "volume": row.get("volume", ""),
            "adj_factor": fmt(adj_factor),
            "adj_open": fmt(adj_open),
            "adj_high": fmt(adj_high),
            "adj_low": fmt(adj_low),
        }

        for window in DEFAULT_SMA_WINDOWS:
            feature[f"sma_{window}"] = (
                fmt(sums[window] / window) if len(queues[window]) == window else ""
            )

        for window in DEFAULT_RETURN_WINDOWS:
            previous_index = len(adj_closes) - window - 1
            previous = adj_closes[previous_index] if previous_index >= 0 else None
            feature[f"ret_{window}"] = (
                fmt(adj_close / previous - 1.0) if previous else ""
            )

        for window, high_window in rolling_highs.items():
            rolling_high = high_window.current(index)
            feature[f"high_{window}"] = fmt(rolling_high)
            feature[f"dd_{window}"] = (
                fmt(adj_close / rolling_high - 1.0) if rolling_high else ""
            )

        output.append(feature)

    return output


def write_feature_rows(features_dir: Path, symbol: str, rows: list[dict[str, str]]) -> None:
    if not rows:
        return

    fieldnames = list(rows[0].keys())
    rows_by_year: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        rows_by_year[row["date"][:4]].append(row)

    for year, year_rows in sorted(rows_by_year.items()):
        year_dir = features_dir / year
        year_dir.mkdir(parents=True, exist_ok=True)
        path = year_dir / f"{symbol}.csv"
        with path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(year_rows)


def write_notes(features_dir: Path) -> None:
    features_dir.mkdir(parents=True, exist_ok=True)
    (features_dir / ".notes").write_text(
        "\n".join(
            [
                "# Daily stock feature dataset notes",
                "",
                "Dataset location: data/stock/features/daily/<year>/<symbol>.csv",
                "",
                "Derived from canonical prices in data/stock/prices/daily/<year>/<symbol>.csv.",
                "Rows are computed per symbol across all available years, then split by calendar year.",
                "Rolling values use adjusted close and require a full actual-trading-row window.",
                "",
                "Added columns:",
                "- adj_factor = adj_close / close",
                "- adj_open, adj_high, adj_low",
                "- sma_20, sma_50, sma_100, sma_150, sma_200",
                "- ret_21, ret_63, ret_126, ret_252",
                "- high_252, dd_252",
                "",
                "Blank OHLCV rows from the canonical data are skipped rather than forward-filled.",
                "",
            ]
        )
    )


def main() -> int:
    args = parse_args()
    rows_by_symbol = read_symbol_rows(args.prices_dir)
    requested = set(args.symbols or rows_by_symbol.keys())
    processed = 0
    written_rows = 0

    for symbol in sorted(requested):
        rows = rows_by_symbol.get(symbol)
        if not rows:
            print(f"skip {symbol}: no rows")
            continue
        features = feature_rows(rows)
        write_feature_rows(args.features_dir, symbol, features)
        processed += 1
        written_rows += len(features)
        print(f"processed {symbol}: rows={len(features)}")

    write_notes(args.features_dir)
    print(f"done: symbols={processed} rows={written_rows} output={args.features_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
