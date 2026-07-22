"""Canonical daily-price CSV persistence for normalized provider data."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


def provider_symbol(prices_dir: Path, storage_symbol: str) -> str:
    """Return the provider symbol recorded in an existing canonical file."""
    for path in sorted(prices_dir.glob(f"*/{storage_symbol}.csv"), reverse=True):
        with path.open(newline="") as handle:
            row = next(csv.DictReader(handle), None)
        if row and row.get("symbol"):
            return row["symbol"]
    return storage_symbol


def storage_symbols_by_provider_symbol(prices_dir: Path) -> dict[str, str]:
    """Map canonical row symbols back to repository filename symbols."""
    mapping: dict[str, str] = {}
    for path in sorted(prices_dir.glob("*/*.csv"), reverse=True):
        with path.open(newline="") as handle:
            row = next(csv.DictReader(handle), None)
        if row and row.get("symbol"):
            mapping.setdefault(row["symbol"], path.stem)
    return mapping


def write_year(
    path: Path,
    rows: list[dict[str, Any]],
    csv_columns: list[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".csv.tmp")
    with temporary.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_columns)
        writer.writeheader()
        writer.writerows(
            {
                column: "" if row.get(column) is None else str(row.get(column))
                for column in csv_columns
            }
            for row in rows
        )
    temporary.replace(path)


def persist(
    prices_dir: Path,
    storage_symbol: str,
    fetched_rows: list[dict[str, Any]],
    csv_columns: list[str],
) -> int:
    """Merge canonical rows by date and atomically rewrite affected year files."""
    rows_by_date: dict[str, dict[str, Any]] = {}
    for path in sorted(prices_dir.glob(f"*/{storage_symbol}.csv")):
        with path.open(newline="") as handle:
            for row in csv.DictReader(handle):
                if row.get("date"):
                    rows_by_date[row["date"]] = row
    for row in fetched_rows:
        if row.get("date"):
            rows_by_date[str(row["date"])] = row

    rows_by_year: dict[str, list[dict[str, Any]]] = {}
    for row in rows_by_date.values():
        date = str(row["date"])
        rows_by_year.setdefault(date[:4], []).append(row)
    for year, rows in rows_by_year.items():
        rows.sort(key=lambda row: str(row["date"]))
        write_year(prices_dir / year / f"{storage_symbol}.csv", rows, csv_columns)
    return len(fetched_rows)
