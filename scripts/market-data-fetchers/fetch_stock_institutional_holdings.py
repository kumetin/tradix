#!/usr/bin/env python3
"""Fetch a current ticker-level institutional-holdings snapshot from Nasdaq."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


URL = "https://api.nasdaq.com/api/company/{symbol}/institutional-holdings"
SOURCE = "nasdaq_institutional_holdings"
CSV_COLUMNS = [
    "symbol",
    "report_period_end",
    "available_date",
    "total_institutional_shares_held",
    "net_reported_shares_change",
    "institutional_holders",
    "source",
    "source_url",
    "fetched_at_utc",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("symbol")
    return parser.parse_args()


def parse_integer(value: Any) -> int | None:
    if value in (None, "", "N/A", "--"):
        return None
    try:
        return int(str(value).replace(",", "").replace("+", "").strip())
    except ValueError:
        return None


def parse_us_date(value: str) -> str:
    return dt.datetime.strptime(value, "%m/%d/%Y").date().isoformat()


def fetch_payload(symbol: str) -> tuple[str, dict[str, Any]]:
    params = urllib.parse.urlencode(
        {
            "limit": 10000,
            "type": "TOTAL",
            "sortColumn": "marketValue",
            "sortOrder": "DESC",
        }
    )
    url = f"{URL.format(symbol=urllib.parse.quote(symbol.upper()))}?{params}"
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; Tradix/1.0)",
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://www.nasdaq.com",
            "Referer": "https://www.nasdaq.com/",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Nasdaq request failed with HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Nasdaq request failed: {exc.reason}") from exc
    if payload.get("status", {}).get("rCode") != 200 or not payload.get("data"):
        raise RuntimeError(f"Nasdaq returned no institutional data for {symbol}")
    return url, payload


def normalize_payload(
    symbol: str,
    source_url: str,
    payload: dict[str, Any],
    fetched_at_utc: str,
) -> dict[str, str]:
    data = payload.get("data") or {}
    holdings_transactions = data.get("holdingsTransactions") or {}
    transactions = (
        (holdings_transactions.get("table") or {}).get("rows") or []
    )
    expected = parse_integer(
        holdings_transactions.get("totalRecords")
    )
    if expected is not None and len(transactions) < expected:
        raise RuntimeError(
            f"Incomplete Nasdaq response for {symbol}: rows={len(transactions)} "
            f"expected={expected}"
        )

    changes = [parse_integer(row.get("sharesChange")) for row in transactions]
    dates = [
        parse_us_date(row["date"])
        for row in transactions
        if row.get("date") not in (None, "", "N/A", "--")
    ]
    active_rows = (data.get("activePositions") or {}).get("rows") or []
    total_row = next(
        (
            row
            for row in active_rows
            if row.get("positions") == "Total Institutional Shares"
        ),
        {},
    )
    total_shares = parse_integer(total_row.get("shares"))
    holders = parse_integer(total_row.get("holders"))
    available_date = dt.datetime.fromisoformat(
        fetched_at_utc.replace("Z", "+00:00")
    ).date().isoformat()
    return {
        "symbol": symbol.upper(),
        "report_period_end": max(dates) if dates else "",
        "available_date": available_date,
        "total_institutional_shares_held": (
            str(total_shares) if total_shares is not None else ""
        ),
        "net_reported_shares_change": (
            str(sum(value for value in changes if value is not None))
            if any(value is not None for value in changes)
            else ""
        ),
        "institutional_holders": str(holders) if holders is not None else "",
        "source": SOURCE,
        "source_url": source_url,
        "fetched_at_utc": fetched_at_utc,
    }


def fetch_stock_institutional_holdings(symbol: str) -> dict[str, str]:
    source_url, payload = fetch_payload(symbol)
    fetched_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    return normalize_payload(symbol, source_url, payload, fetched_at)


def rows_to_csv(rows: list[dict[str, str]]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def main() -> int:
    args = parse_args()
    try:
        row = fetch_stock_institutional_holdings(args.symbol)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    sys.stdout.write(rows_to_csv([row]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
