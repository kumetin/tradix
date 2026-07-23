#!/usr/bin/env python3
"""Import unresolved historical S&P prices from a local FNSPID archive."""

from __future__ import annotations

import argparse
import csv
import io
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PRICE_ROOT = ROOT / "data/stock/prices/daily"
FIRST_REPORT = ROOT / "data/stock/universes/sp500-historical-price-fill.csv"
OUTPUT_REPORT = ROOT / "data/stock/universes/sp500-historical-price-fill-fnspid.csv"
CSV_COLUMNS = [
    "symbol", "datetime", "date", "bar_size", "open", "high", "low", "close",
    "adj_close", "volume", "currency", "exchange_timezone", "source",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    unresolved = [
        row["historical_ticker"]
        for row in csv.DictReader(FIRST_REPORT.open(newline="", encoding="utf-8"))
        if row["status"] == "unresolved"
    ]
    results = []
    with zipfile.ZipFile(args.archive) as archive:
        names = set(archive.namelist())
        for ticker in unresolved:
            member = f"full_history/{ticker.replace('.', '-')}.csv"
            if member not in names:
                results.append(result(ticker, "unresolved", 0, "archive file absent"))
                continue
            source_rows = list(csv.DictReader(io.TextIOWrapper(
                archive.open(member), encoding="utf-8"
            )))
            rows = []
            for source in source_rows:
                date = source.get("date", "")
                if not ("2014-01-01" <= date <= "2022-01-31"):
                    continue
                values = [
                    source.get("open"), source.get("high"), source.get("low"),
                    source.get("close"), source.get("adj close"),
                ]
                if not all(valid_positive(value) for value in values):
                    continue
                rows.append({
                    "symbol": ticker.replace(".", "-"),
                    "datetime": f"{date}T00:00:00+00:00",
                    "date": date, "bar_size": "1d",
                    "open": source["open"], "high": source["high"],
                    "low": source["low"], "close": source["close"],
                    "adj_close": source["adj close"],
                    "volume": source.get("volume", ""), "currency": "USD",
                    "exchange_timezone": "America/New_York",
                    "source": "fnspid_yahoo_archive_2023-12-30",
                })
            if not rows:
                results.append(result(ticker, "unresolved", 0, "no valid rows in range"))
                continue
            persist(ticker.replace(".", "-"), rows)
            results.append(result(ticker, "persisted", len(rows), ""))
    write_csv(OUTPUT_REPORT, results)
    print(
        f"persisted={sum(row['status'] == 'persisted' for row in results)} "
        f"unresolved={sum(row['status'] != 'persisted' for row in results)}"
    )
    print(OUTPUT_REPORT.relative_to(ROOT))
    return 0


def valid_positive(value: str | None) -> bool:
    try:
        return value not in (None, "") and float(value) > 0
    except ValueError:
        return False


def result(ticker: str, status: str, count: int, reason: str) -> dict[str, Any]:
    return {
        "historical_ticker": ticker, "status": status,
        "row_count": count, "reason": reason,
    }


def persist(ticker: str, rows: list[dict[str, Any]]) -> None:
    by_year: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_year[row["date"][:4]].append(row)
    for year, year_rows in by_year.items():
        path = PRICE_ROOT / year / f"{ticker}.csv"
        existing = []
        if path.exists():
            with path.open(newline="", encoding="utf-8") as handle:
                existing = list(csv.DictReader(handle))
        merged = {
            row["date"]: {column: row.get(column, "") for column in CSV_COLUMNS}
            for row in existing + year_rows if row.get("date")
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        write_csv(path, [merged[date] for date in sorted(merged)])


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(rows[0]) if rows else CSV_COLUMNS
        )
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    raise SystemExit(main())
