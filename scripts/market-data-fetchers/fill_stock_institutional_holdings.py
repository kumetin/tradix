#!/usr/bin/env python3
"""Fetch and persist current institutional-holdings snapshots."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
FETCHER_PATH = Path(__file__).with_name("fetch_stock_institutional_holdings.py")
DEFAULT_DATASET_DIR = REPO_ROOT / "data/stock/institutions/quarterly"
DEFAULT_PRICES_DIR = REPO_ROOT / "data/stock/prices/daily"

spec = importlib.util.spec_from_file_location("fetch_stock_institutional_holdings", FETCHER_PATH)
fetcher = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(fetcher)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", action="append", dest="symbols", default=[])
    parser.add_argument("--all-local-symbols", action="store_true")
    parser.add_argument("--prices-dir", type=Path, default=DEFAULT_PRICES_DIR)
    parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET_DIR)
    parser.add_argument("--workers", type=int, default=4)
    return parser.parse_args()


def local_symbols(prices_dir: Path) -> set[str]:
    return {path.stem for path in prices_dir.glob("*/*.csv")}


def persist(dataset_dir: Path, row: dict[str, str]) -> None:
    symbol = row["symbol"]
    path = dataset_dir / row["available_date"][:4] / f"{symbol}.csv"
    existing = {}
    if path.exists():
        with path.open(newline="") as handle:
            existing = {item["available_date"]: item for item in csv.DictReader(handle)}
    existing[row["available_date"]] = row
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".csv.tmp")
    with temporary.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fetcher.CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(existing[key] for key in sorted(existing))
    temporary.replace(path)


def main() -> int:
    args = parse_args()
    symbols = {symbol.upper() for symbol in args.symbols}
    if args.all_local_symbols:
        symbols.update(local_symbols(args.prices_dir))
    if not symbols:
        raise SystemExit("Select --symbol TICKER or --all-local-symbols.")

    failures = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {
            pool.submit(fetcher.fetch_stock_institutional_holdings, symbol): symbol
            for symbol in sorted(symbols)
        }
        for future in as_completed(futures):
            symbol = futures[future]
            try:
                row = future.result()
                persist(args.dataset_dir, row)
                print(
                    f"{symbol}: net_change={row['net_reported_shares_change']}",
                    flush=True,
                )
            except Exception as exc:
                failures.append(symbol)
                print(f"{symbol}: unavailable: {exc}", file=sys.stderr, flush=True)
    print(f"done: symbols={len(symbols)} failures={len(failures)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
