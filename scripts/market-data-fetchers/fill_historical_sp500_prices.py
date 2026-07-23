#!/usr/bin/env python3
"""Fill recoverable price histories for dated S&P 500 members."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
MEMBERSHIP = ROOT / "data/stock/universes/sp500-historical-membership.csv"
PRICE_ROOT = ROOT / "data/stock/prices/daily"
FETCHER_PATH = ROOT / "scripts/market-data-fetchers/fetch_stock_prices.py"
START = "2015-01-01"
END = "2022-01-31"
PURE_RENAMES = {
    "ABC": "COR",
    "ANTM": "ELV",
    "BLL": "BALL",
    "COG": "CTRA",
    "CTL": "LUMN",
    "FB": "META",
    "FLT": "CPAY",
    "NLOK": "GEN",
    "PKI": "RVTY",
    "SYMC": "GEN",
    "WLTW": "WTW",
}
CSV_COLUMNS = [
    "symbol", "datetime", "date", "bar_size", "open", "high", "low", "close",
    "adj_close", "volume", "currency", "exchange_timezone", "source",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    fetcher = load_module(FETCHER_PATH, "historical_sp500_price_fetcher")
    intervals = membership_intervals()
    existing = {
        path.stem for path in PRICE_ROOT.glob("*/*.csv")
    }
    missing = sorted(ticker for ticker in intervals if local_name(ticker) not in existing)
    print(f"missing_before={len(missing)}")
    if args.dry_run:
        print(",".join(missing))
        return 0

    fetched: dict[str, list[dict[str, Any]]] = {}
    failures: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(
                fetcher.fetch_historical_rows,
                PURE_RENAMES.get(ticker, ticker).replace(".", "-"),
                START,
                END,
                "1d",
            ): ticker
            for ticker in missing
        }
        for future in as_completed(futures):
            ticker = futures[future]
            try:
                rows = future.result()
                overlap = [
                    row for row in rows
                    if overlaps_membership(row.get("date", ""), intervals[ticker])
                ]
                if not overlap:
                    failures[ticker] = "no rows overlapping membership interval"
                    continue
                for row in rows:
                    row["symbol"] = local_name(ticker)
                    row["source"] = (
                        f"{row.get('source', '')};requested_provider_symbol="
                        f"{PURE_RENAMES.get(ticker, ticker)}"
                    )
                fetched[ticker] = [row for row in rows if valid_price_row(row)]
            except Exception as exc:
                failures[ticker] = str(exc)

    for ticker, rows in sorted(fetched.items()):
        persist(local_name(ticker), rows)
    report = ROOT / "data/stock/universes/sp500-historical-price-fill.csv"
    report_rows = [
        {
            "historical_ticker": ticker,
            "provider_ticker": PURE_RENAMES.get(ticker, ticker),
            "status": "persisted" if ticker in fetched else "unresolved",
            "row_count": len(fetched.get(ticker, [])),
            "reason": failures.get(ticker, ""),
        }
        for ticker in missing
    ]
    write_csv(report, report_rows)
    print(f"persisted={len(fetched)} unresolved={len(failures)}")
    print(report.relative_to(ROOT))
    return 0


def membership_intervals() -> dict[str, tuple[str, str]]:
    dates: dict[str, list[str]] = defaultdict(list)
    with MEMBERSHIP.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if "2014-01-01" <= row["date"] <= "2021-12-31":
                for ticker in row["tickers"].split(","):
                    dates[ticker].append(row["date"])
    return {
        ticker: (min(values), max(values))
        for ticker, values in dates.items()
    }


def local_name(ticker: str) -> str:
    return ticker.replace(".", "-")


def overlaps_membership(date: str, interval: tuple[str, str]) -> bool:
    return bool(date) and interval[0] <= date <= interval[1]


def valid_price_row(row: dict[str, Any]) -> bool:
    try:
        return all(
            row.get(field) not in (None, "") and float(row[field]) > 0
            for field in ("open", "high", "low", "close", "adj_close")
        )
    except (TypeError, ValueError):
        return False


def persist(ticker: str, rows: list[dict[str, Any]]) -> None:
    by_year: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("date"):
            by_year[row["date"][:4]].append(row)
    for year, year_rows in by_year.items():
        path = PRICE_ROOT / year / f"{ticker}.csv"
        existing = []
        if path.exists():
            with path.open(newline="", encoding="utf-8") as handle:
                existing = list(csv.DictReader(handle))
        merged = {
            row["date"]: {column: row.get(column, "") for column in CSV_COLUMNS}
            for row in existing + year_rows
            if row.get("date")
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        write_csv(path, [merged[date] for date in sorted(merged)])


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=(
            list(rows[0]) if rows else CSV_COLUMNS
        ))
        writer.writeheader()
        writer.writerows(rows)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    raise SystemExit(main())
