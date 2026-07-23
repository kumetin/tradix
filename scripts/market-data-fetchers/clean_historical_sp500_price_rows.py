#!/usr/bin/env python3
"""Remove invalid imported OHLCV rows while preserving valid history boundaries."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PRICE_ROOT = ROOT / "data/stock/prices/daily"
REPORTS = (
    ROOT / "data/stock/universes/sp500-historical-price-fill.csv",
    ROOT / "data/stock/universes/sp500-historical-price-fill-fnspid.csv",
)


def main() -> int:
    tickers = set()
    for report in REPORTS:
        with report.open(newline="", encoding="utf-8") as handle:
            tickers.update(
                row["historical_ticker"].replace(".", "-")
                for row in csv.DictReader(handle)
                if row["status"] == "persisted"
            )
    removed = 0
    for ticker in sorted(tickers):
        for path in sorted(PRICE_ROOT.glob(f"*/{ticker}.csv")):
            with path.open(newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                fieldnames = reader.fieldnames
                rows = list(reader)
            valid = [row for row in rows if valid_row(row)]
            removed += len(rows) - len(valid)
            if len(valid) != len(rows):
                with path.open("w", newline="", encoding="utf-8") as handle:
                    writer = csv.DictWriter(handle, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(valid)
    print(f"symbols={len(tickers)} removed_invalid_rows={removed}")
    return 0


def valid_row(row: dict[str, str]) -> bool:
    try:
        return all(
            row.get(field) not in (None, "") and float(row[field]) > 0
            for field in ("open", "high", "low", "close", "adj_close")
        )
    except ValueError:
        return False


if __name__ == "__main__":
    raise SystemExit(main())
