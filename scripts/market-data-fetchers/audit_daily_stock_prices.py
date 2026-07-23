#!/usr/bin/env python3
"""Audit canonical daily prices without conflating history boundaries."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PRICES_DIR = ROOT / "data/stock/prices/daily"
OHLCV_FIELDS = ("open", "high", "low", "close", "adj_close", "volume")


def parse_args(argv: Sequence[str] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prices-dir", type=Path, default=DEFAULT_PRICES_DIR)
    parser.add_argument("--reference-symbol", default="SPY")
    parser.add_argument("--output", type=Path, help="Write Markdown instead of stdout.")
    return parser.parse_args(argv)


def symbol_files(prices_dir: Path) -> Dict[str, List[Path]]:
    grouped: Dict[str, List[Path]] = {}
    for path in sorted(prices_dir.glob("*/*.csv")):
        grouped.setdefault(path.stem, []).append(path)
    return grouped


def read_rows(paths: Iterable[Path]) -> List[dict]:
    rows: List[dict] = []
    for path in paths:
        with path.open(newline="", encoding="utf-8") as handle:
            rows.extend(csv.DictReader(handle))
    return rows


def valid_price_row(row: dict) -> bool:
    return bool(row.get("date")) and all(row.get(field) not in (None, "") for field in OHLCV_FIELDS)


def audit(prices_dir: Path, reference_symbol: str) -> str:
    files = symbol_files(prices_dir)
    if reference_symbol not in files:
        raise ValueError("reference symbol {} is absent".format(reference_symbol))

    reference_rows = [row for row in read_rows(files[reference_symbol]) if valid_price_row(row)]
    reference_dates = sorted({row["date"] for row in reference_rows})
    reference_timezone = reference_rows[-1].get("exchange_timezone", "")

    internal_gaps: List[Tuple[str, List[str]]] = []
    invalid_rows: List[Tuple[str, List[str]]] = []
    duplicate_rows: List[Tuple[str, List[str]]] = []
    unsupported_calendars: Counter = Counter()
    valid_symbol_count = 0

    for symbol, paths in sorted(files.items()):
        rows = [row for row in read_rows(paths) if row.get("date")]
        valid = [row for row in rows if valid_price_row(row)]
        bad_dates = sorted({row["date"] for row in rows if not valid_price_row(row)})
        duplicates = sorted(date for date, count in Counter(row["date"] for row in rows).items() if count > 1)
        if bad_dates:
            invalid_rows.append((symbol, bad_dates))
        if duplicates:
            duplicate_rows.append((symbol, duplicates))
        if not valid:
            continue

        valid_symbol_count += 1
        dates = {row["date"] for row in valid}
        first_date = min(dates)
        last_date = max(dates)
        timezone = valid[-1].get("exchange_timezone", "")
        if timezone != reference_timezone:
            unsupported_calendars[timezone or "unknown"] += 1
            continue

        missing = [date for date in reference_dates if first_date <= date <= last_date and date not in dates]
        if missing:
            internal_gaps.append((symbol, missing))

    lines = [
        "# Daily Stock Price Integrity Audit",
        "",
        "Reference symbol: `{}` (`{}`)".format(reference_symbol, reference_timezone),
        "",
        "- Symbols with at least one valid row: `{}`".format(valid_symbol_count),
        "- Symbols with supported-calendar internal gaps: `{}`".format(len(internal_gaps)),
        "- Symbols with invalid OHLCV rows: `{}`".format(len(invalid_rows)),
        "- Symbols with duplicate dates: `{}`".format(len(duplicate_rows)),
        "",
        "Observed-history boundaries are not counted as missing. Symbols on other exchange timezones are not compared with the reference calendar.",
        "",
        "## Supported-Calendar Internal Gaps",
        "",
    ]
    if internal_gaps:
        for symbol, dates in internal_gaps:
            lines.append("- `{}`: `{}` gaps; {}".format(symbol, len(dates), ", ".join(dates[:20])))
    else:
        lines.append("None.")

    lines.extend(["", "## Invalid OHLCV Rows", ""])
    if invalid_rows:
        for symbol, dates in invalid_rows:
            lines.append("- `{}`: {}".format(symbol, ", ".join(dates)))
    else:
        lines.append("None.")

    lines.extend(["", "## Duplicate Dates", ""])
    if duplicate_rows:
        for symbol, dates in duplicate_rows:
            lines.append("- `{}`: {}".format(symbol, ", ".join(dates)))
    else:
        lines.append("None.")

    lines.extend(["", "## Unsupported Exchange Calendars", ""])
    if unsupported_calendars:
        for timezone, count in sorted(unsupported_calendars.items()):
            lines.append("- `{}`: `{}` symbols; no missing-session claim made".format(timezone, count))
    else:
        lines.append("None.")
    lines.append("")
    return "\n".join(lines)


def main(argv: Sequence[str] = None) -> int:
    args = parse_args(argv)
    report = audit(args.prices_dir, args.reference_symbol)
    if args.output:
        args.output.write_text(report, encoding="utf-8")
    else:
        print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
