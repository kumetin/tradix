#!/usr/bin/env python3
"""Fetch and persist SEC quarterly fundamentals for local or explicit symbols."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import os
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
FETCHER_PATH = Path(__file__).with_name("fetch_stock_fundamentals.py")
DEFAULT_DATASET_DIR = REPO_ROOT / "data/stock/fundamentals/quarterly"
DEFAULT_PRICES_DIR = REPO_ROOT / "data/stock/prices/daily"

spec = importlib.util.spec_from_file_location("fetch_stock_fundamentals", FETCHER_PATH)
fetcher = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(fetcher)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-date", default="2014-01-01")
    parser.add_argument("--end-date", default="9999-12-31")
    parser.add_argument("--symbol", action="append", dest="symbols", default=[])
    parser.add_argument("--all-local-symbols", action="store_true")
    parser.add_argument(
        "--start-symbol",
        help="Resume an alphabetic all-local run at this symbol (inclusive).",
    )
    parser.add_argument("--prices-dir", type=Path, default=DEFAULT_PRICES_DIR)
    parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET_DIR)
    parser.add_argument("--user-agent", default=os.environ.get("SEC_USER_AGENT"))
    parser.add_argument(
        "--request-interval",
        type=float,
        default=0.12,
        help="Seconds between SEC requests; default remains below 10 requests/second.",
    )
    parser.add_argument("--workers", type=int, default=4)
    return parser.parse_args()


def local_symbols(prices_dir: Path) -> list[str]:
    return sorted({path.stem for path in prices_dir.glob("*/*.csv")})


def row_key(row: dict[str, str]) -> tuple[str, str]:
    return row.get("fiscal_period_end", ""), row.get("available_date", "")


def read_existing(dataset_dir: Path, symbol: str) -> dict[tuple[str, str], dict[str, str]]:
    rows = {}
    for path in sorted(dataset_dir.glob(f"*/{symbol}.csv")):
        with path.open(newline="") as handle:
            for row in csv.DictReader(handle):
                rows[row_key(row)] = row
    return rows


def persist(dataset_dir: Path, symbol: str, fetched: list[dict[str, str]]) -> int:
    rows = read_existing(dataset_dir, symbol)
    for row in fetched:
        rows[row_key(row)] = row
    by_year: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows.values():
        available_date = row.get("available_date", "")
        if len(available_date) >= 4:
            by_year[available_date[:4]].append(row)
    for year, year_rows in by_year.items():
        year_rows.sort(key=lambda row: (row["available_date"], row["fiscal_period_end"]))
        destination = dataset_dir / year / f"{symbol}.csv"
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(".csv.tmp")
        with temporary.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fetcher.CSV_COLUMNS)
            writer.writeheader()
            writer.writerows(
                {column: row.get(column, "") for column in fetcher.CSV_COLUMNS}
                for row in year_rows
            )
        temporary.replace(destination)
    return len(fetched)


def main() -> int:
    args = parse_args()
    if not args.user_agent or "@" not in args.user_agent:
        raise SystemExit(
            "Set SEC_USER_AGENT='Tradix your-email@example.com' before fetching."
        )
    symbols = {symbol.upper() for symbol in args.symbols}
    if args.all_local_symbols:
        symbols.update(local_symbols(args.prices_dir))
    if args.start_symbol:
        symbols = {symbol for symbol in symbols if symbol >= args.start_symbol.upper()}
    if not symbols:
        raise SystemExit("Select --symbol TICKER or --all-local-symbols.")

    ticker_payload = fetcher.fetch_json(fetcher.TICKERS_URL, args.user_agent)
    skipped: list[str] = []
    eligible: list[tuple[str, str]] = []
    for symbol in sorted(symbols):
        cik = fetcher.ticker_to_cik(ticker_payload, symbol)
        if cik is None:
            skipped.append(symbol)
            print(f"{symbol}: skipped (no SEC CIK)", flush=True)
            continue
        eligible.append((symbol, cik))

    def fetch_one(symbol: str, cik: str):
        time.sleep(max(0.0, args.request_interval))
        payload = fetcher.fetch_json(
            fetcher.COMPANY_FACTS_URL.format(cik=cik), args.user_agent
        )
        rows = fetcher.normalize_company_facts(
            symbol, payload, args.start_date, args.end_date
        )
        return symbol, persist(args.dataset_dir, symbol, rows)

    failures: list[str] = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {
            pool.submit(fetch_one, symbol, cik): symbol for symbol, cik in eligible
        }
        for future in as_completed(futures):
            symbol = futures[future]
            try:
                _, count = future.result()
                print(f"{symbol}: fetched={count}", flush=True)
            except Exception as exc:
                failures.append(symbol)
                print(f"{symbol}: ERROR: {exc}", file=sys.stderr, flush=True)
    print(
        f"done: symbols={len(symbols)} failures={len(failures)} "
        f"no_cik={len(skipped)}"
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
