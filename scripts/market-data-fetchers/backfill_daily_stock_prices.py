#!/usr/bin/env python3
"""Backfill the repository daily-price dataset for all existing symbols."""

from __future__ import annotations

import argparse
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
CANONICAL_PATH = Path(__file__).with_name("stock_price_canonical.py")
canonical_spec = importlib.util.spec_from_file_location(
    "stock_price_canonical", CANONICAL_PATH
)
canonical = importlib.util.module_from_spec(canonical_spec)
assert canonical_spec.loader is not None
canonical_spec.loader.exec_module(canonical)


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


def fetch(
    storage_symbol: str,
    start_date: str,
    end_date: str,
    prices_dir: Path,
):
    market_symbol = canonical.provider_symbol(prices_dir, storage_symbol)
    return storage_symbol, fetcher.fetch_historical_rows(
        market_symbol, start_date, end_date, "1d"
    )


def main() -> int:
    args = parse_args()
    symbols = sorted(set(args.symbols or existing_symbols(args.prices_dir)))
    failures = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(
                fetch,
                symbol,
                args.start_date,
                args.end_date,
                args.prices_dir,
            ): symbol
            for symbol in symbols
        }
        for future in as_completed(futures):
            symbol = futures[future]
            try:
                _, rows = future.result()
                count = canonical.persist(
                    args.prices_dir, symbol, rows, fetcher.CSV_COLUMNS
                )
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
