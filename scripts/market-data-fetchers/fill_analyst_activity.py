#!/usr/bin/env python3
"""Fill the repository analyst-activity dataset for symbols or watchlists.

Parameters:
    Required ``--start-date`` and ``--end-date`` bound activity. ``--dataset-dir``
    selects storage; repeatable ``--watchlist`` and ``--symbol`` inputs select
    securities; ``--source`` selects MarketBeat or Finnhub; ``--workers`` sets
    fetch concurrency. Finnhub also reads ``FINNHUB_API_KEY``.
External sources:
    Local watchlist Markdown files plus analyst data fetched by
    ``fetch_analyst_activity.py`` from MarketBeat or Finnhub.
Side effects:
    Performs concurrent HTTPS requests and atomically creates or replaces
    per-year analyst CSVs; prints progress and failures.
Examples:
    Fill activity for explicit symbols::

        python3 scripts/market-data-fetchers/fill_analyst_activity.py --start-date 2026-01-01 --end-date 2026-06-30 --symbol AAPL --symbol MSFT

    Fill every ticker parsed from a watchlist using Finnhub::

        python3 scripts/market-data-fetchers/fill_analyst_activity.py --start-date 2026-01-01 --end-date 2026-06-30 --watchlist watchlists/ai-infrastructure.md --source finnhub
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
FETCHER_PATH = Path(__file__).with_name("fetch_analyst_activity.py")
DEFAULT_DATASET_DIR = REPO_ROOT / "data/stock/analysts/activity"
WATCHLIST_TICKER_RE = re.compile(r"^\s*[-*]\s+([A-Z][A-Z0-9.-]{0,9})(?:\s|:|-|$)")

spec = importlib.util.spec_from_file_location("fetch_analyst_activity", FETCHER_PATH)
fetcher = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(fetcher)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=DEFAULT_DATASET_DIR,
        help="Destination dataset root. Defaults to data/stock/analysts/activity.",
    )
    parser.add_argument("--watchlist", type=Path, action="append", default=[])
    parser.add_argument("--symbol", action="append", dest="symbols", default=[])
    parser.add_argument(
        "--source",
        choices=("marketbeat", "finnhub"),
        default="marketbeat",
        help="Data source. marketbeat is free/public HTML and requires no key.",
    )
    parser.add_argument("--workers", type=int, default=4)
    return parser.parse_args()


def parse_watchlist_symbols(path: Path) -> list[str]:
    symbols: list[str] = []
    with path.open() as handle:
        for line in handle:
            match = WATCHLIST_TICKER_RE.match(line)
            if match:
                symbols.append(normalize_symbol(match.group(1)))
    return symbols


def normalize_symbol(symbol: str) -> str:
    return symbol.strip().upper()


def fetch_with_source(symbol: str, start_date: str, end_date: str, source: str):
    return symbol, fetcher.fetch_analyst_activity_rows(symbol, start_date, end_date, source)


def row_key(row: dict) -> tuple[str, ...]:
    return (
        row.get("symbol", ""),
        row.get("datetime", ""),
        row.get("firm", ""),
        row.get("analyst", ""),
        row.get("from_grade", ""),
        row.get("to_grade", ""),
        row.get("from_price_target", ""),
        row.get("to_price_target", ""),
        row.get("action", ""),
    )


def read_existing_rows(dataset_dir: Path, symbol: str) -> dict[tuple[str, str, str, str, str, str], dict]:
    rows = {}
    for path in sorted(dataset_dir.glob(f"*/{symbol}.csv")):
        with path.open(newline="") as handle:
            for row in csv.DictReader(handle):
                rows[row_key(row)] = row
    return rows


def write_year(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".csv.tmp")
    with temporary.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fetcher.CSV_COLUMNS)
        writer.writeheader()
        writer.writerows({column: row.get(column, "") for column in fetcher.CSV_COLUMNS} for row in rows)
    temporary.replace(path)


def persist(dataset_dir: Path, symbol: str, fetched_rows: list[dict]) -> int:
    rows_by_key = read_existing_rows(dataset_dir, symbol)
    for row in fetched_rows:
        if row.get("date"):
            rows_by_key[row_key(row)] = row

    rows_by_year: dict[str, list[dict]] = {}
    for row in rows_by_key.values():
        date = row.get("date", "")
        if len(date) >= 4:
            rows_by_year.setdefault(date[:4], []).append(row)

    for year, rows in rows_by_year.items():
        rows.sort(key=lambda row: (row.get("date", ""), row.get("datetime", ""), row.get("firm", "")))
        write_year(dataset_dir / year / f"{symbol}.csv", rows)
    return len(fetched_rows)


def selected_symbols(args: argparse.Namespace) -> list[str]:
    symbols = [normalize_symbol(symbol) for symbol in args.symbols]
    for watchlist in args.watchlist:
        symbols.extend(parse_watchlist_symbols(watchlist))
    return sorted(set(symbol for symbol in symbols if symbol))


def main() -> int:
    args = parse_args()
    symbols = selected_symbols(args)
    if not symbols:
        raise SystemExit("No symbols selected. Use --symbol or --watchlist.")

    failures = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(fetch_with_source, symbol, args.start_date, args.end_date, args.source): symbol
            for symbol in symbols
        }
        for future in as_completed(futures):
            symbol = futures[future]
            try:
                _, rows = future.result()
                count = persist(args.dataset_dir, symbol, rows)
                print(f"{symbol}: fetched={count}", flush=True)
            except Exception as exc:
                failures.append(symbol)
                print(f"{symbol}: ERROR: {exc}", file=sys.stderr, flush=True)

    print(f"done: symbols={len(symbols)} failures={len(failures)}")
    if failures:
        print("failed symbols: " + " ".join(sorted(failures)), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
