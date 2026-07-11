#!/usr/bin/env python3
"""Backfill the repository daily-price dataset for all existing symbols."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
FETCHER_PATH = Path(__file__).with_name("fetch_stock_prices.py")
spec = importlib.util.spec_from_file_location("fetch_stock_prices", FETCHER_PATH)
fetcher = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(fetcher)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("start_date")
    parser.add_argument("end_date")
    parser.add_argument(
        "--prices-dir",
        type=Path,
        default=REPO_ROOT / "data/stock/prices/daily",
    )
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--symbol", action="append", dest="symbols")
    return parser.parse_args()


def existing_symbols(prices_dir: Path) -> list[str]:
    return sorted({path.stem for path in prices_dir.glob("*/*.csv")})


def fetch(symbol: str, start_date: str, end_date: str):
    return symbol, fetcher.fetch_historical_rows(symbol, start_date, end_date, "1d")


def write_year(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".csv.tmp")
    with temporary.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fetcher.CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(
            {column: fetcher.format_csv_value(row.get(column)) for column in fetcher.CSV_COLUMNS}
            for row in rows
        )
    temporary.replace(path)


def persist(prices_dir: Path, symbol: str, fetched_rows: list[dict]) -> int:
    rows_by_date = {}
    for path in sorted(prices_dir.glob(f"*/{symbol}.csv")):
        with path.open(newline="") as handle:
            for row in csv.DictReader(handle):
                if row.get("date"):
                    rows_by_date[row["date"]] = row
    for row in fetched_rows:
        if row.get("date"):
            rows_by_date[row["date"]] = row

    rows_by_year = {}
    for row in rows_by_date.values():
        rows_by_year.setdefault(row["date"][:4], []).append(row)
    for year, rows in rows_by_year.items():
        rows.sort(key=lambda row: row["date"])
        write_year(prices_dir / year / f"{symbol}.csv", rows)
    return len(fetched_rows)


def main() -> int:
    args = parse_args()
    symbols = sorted(set(args.symbols or existing_symbols(args.prices_dir)))
    failures = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(fetch, symbol, args.start_date, args.end_date): symbol
            for symbol in symbols
        }
        for future in as_completed(futures):
            symbol = futures[future]
            try:
                _, rows = future.result()
                count = persist(args.prices_dir, symbol, rows)
                print(f"{symbol}: fetched={count}", flush=True)
            except Exception as exc:  # continue so transient failures can be retried
                failures.append(symbol)
                print(f"{symbol}: ERROR: {exc}", file=sys.stderr, flush=True)

    print(f"done: symbols={len(symbols)} failures={len(failures)}")
    if failures:
        print("failed symbols: " + " ".join(sorted(failures)), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
