#!/usr/bin/env python3
"""Fetch point-in-time quarterly fundamentals from SEC Company Facts.

Set ``SEC_USER_AGENT`` to an identifying application/contact string as required
by SEC automated-access policy. The normalized CSV is written to stdout.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import os
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import date
from typing import Any


TICKERS_URL = "https://www.sec.gov/files/company_tickers_exchange.json"
COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
SOURCE = "sec_companyfacts"
FORMS = {"10-Q", "10-Q/A", "10-K", "10-K/A", "20-F", "20-F/A", "40-F", "40-F/A"}
CSV_COLUMNS = [
    "symbol",
    "fiscal_period_end",
    "available_date",
    "diluted_eps",
    "revenue",
    "net_income",
    "total_debt",
    "institutional_ownership_pct",
    "currency",
    "source",
    "accession",
]

DURATION_CONCEPTS = {
    "diluted_eps": (
        ("us-gaap", "EarningsPerShareDiluted"),
        ("ifrs-full", "DilutedEarningsLossPerShare"),
    ),
    "revenue": (
        ("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax"),
        ("us-gaap", "Revenues"),
        ("us-gaap", "SalesRevenueNet"),
        ("ifrs-full", "Revenue"),
    ),
    "net_income": (
        ("us-gaap", "NetIncomeLoss"),
        ("us-gaap", "ProfitLoss"),
        ("ifrs-full", "ProfitLoss"),
    ),
}
DEBT_CONCEPTS = (
    ("us-gaap", "LongTermDebtAndFinanceLeaseObligations"),
    ("us-gaap", "LongTermDebtAndCapitalLeaseObligations"),
    ("us-gaap", "LongTermDebt"),
    ("ifrs-full", "Borrowings"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("symbol")
    parser.add_argument("--start-date", default="2014-01-01")
    parser.add_argument("--end-date", default=date.today().isoformat())
    parser.add_argument("--user-agent", default=os.environ.get("SEC_USER_AGENT"))
    return parser.parse_args()


def fetch_json(url: str, user_agent: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = response.read()
            if response.headers.get("Content-Encoding", "").lower() == "gzip":
                body = gzip.decompress(body)
            return json.loads(body.decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"SEC request failed with HTTP {exc.code}: {url}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"SEC request failed: {exc.reason}") from exc


def ticker_to_cik(payload: dict[str, Any], symbol: str) -> str | None:
    fields = payload.get("fields", [])
    try:
        ticker_index = fields.index("ticker")
        cik_index = fields.index("cik")
    except ValueError:
        raise RuntimeError("Unexpected SEC ticker-map schema")
    provider_symbol = symbol.upper().replace(".", "-")
    for row in payload.get("data", []):
        if str(row[ticker_index]).upper().replace(".", "-") == provider_symbol:
            return str(row[cik_index]).zfill(10)
    return None


def fact_units(payload: dict[str, Any], taxonomy: str, concept: str) -> list[dict[str, Any]]:
    fact = payload.get("facts", {}).get(taxonomy, {}).get(concept, {})
    rows: list[dict[str, Any]] = []
    for unit, values in fact.get("units", {}).items():
        for value in values:
            copied = dict(value)
            copied["_unit"] = unit
            rows.append(copied)
    return rows


def duration_days(row: dict[str, Any]) -> int | None:
    try:
        return (date.fromisoformat(row["end"]) - date.fromisoformat(row["start"])).days
    except (KeyError, TypeError, ValueError):
        return None


def normalized_duration_facts(
    payload: dict[str, Any], concepts: tuple[tuple[str, str], ...]
) -> list[dict[str, Any]]:
    """Use genuinely quarterly contexts; reject YTD and annual durations."""
    for taxonomy, concept in concepts:
        candidates = [
            row
            for row in fact_units(payload, taxonomy, concept)
            if row.get("form") in FORMS
            and row.get("filed")
            and row.get("end")
            and duration_days(row) is not None
            and 65 <= duration_days(row) <= 115
        ]
        if candidates:
            return candidates
    return []


def normalized_instant_facts(
    payload: dict[str, Any], concepts: tuple[tuple[str, str], ...]
) -> list[dict[str, Any]]:
    for taxonomy, concept in concepts:
        candidates = [
            row
            for row in fact_units(payload, taxonomy, concept)
            if row.get("form") in FORMS and row.get("filed") and row.get("end")
        ]
        if candidates:
            return candidates
    return []


def choose_visible_versions(rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    """Keep one filed version per period and availability date."""
    selected: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        key = (str(row["end"]), str(row["filed"]))
        previous = selected.get(key)
        # Prefer the latest accession when amendments or duplicate contexts exist.
        if previous is None or str(row.get("accn", "")) > str(previous.get("accn", "")):
            selected[key] = row
    return selected


def normalize_company_facts(
    symbol: str,
    payload: dict[str, Any],
    start_date: str,
    end_date: str,
) -> list[dict[str, str]]:
    field_rows = {
        field: choose_visible_versions(normalized_duration_facts(payload, concepts))
        for field, concepts in DURATION_CONCEPTS.items()
    }
    field_rows["total_debt"] = choose_visible_versions(
        normalized_instant_facts(payload, DEBT_CONCEPTS)
    )

    observations: dict[tuple[str, str], dict[str, str]] = {}
    for field, values in field_rows.items():
        for (period_end, filed), raw in values.items():
            if not (start_date <= filed <= end_date):
                continue
            key = (period_end, filed)
            row = observations.setdefault(
                key,
                {
                    "symbol": symbol.upper(),
                    "fiscal_period_end": period_end,
                    "available_date": filed,
                    "diluted_eps": "",
                    "revenue": "",
                    "net_income": "",
                    "total_debt": "",
                    "institutional_ownership_pct": "",
                    "currency": "",
                    "source": SOURCE,
                    "accession": "",
                },
            )
            row[field] = str(raw.get("val", ""))
            unit = str(raw.get("_unit", ""))
            if field != "diluted_eps" and unit:
                row["currency"] = unit
            row["accession"] = str(raw.get("accn", ""))

    rows = list(observations.values())
    rows.sort(key=lambda row: (row["available_date"], row["fiscal_period_end"]))
    return rows


def fetch_stock_fundamental_rows(
    symbol: str,
    start_date: str,
    end_date: str,
    user_agent: str,
) -> list[dict[str, str]]:
    if not user_agent or "@" not in user_agent:
        raise ValueError(
            "Set SEC_USER_AGENT to an identifying application and contact email"
        )
    cik = ticker_to_cik(fetch_json(TICKERS_URL, user_agent), symbol)
    if cik is None:
        raise RuntimeError(f"No SEC CIK mapping for {symbol}")
    payload = fetch_json(COMPANY_FACTS_URL.format(cik=cik), user_agent)
    return normalize_company_facts(symbol, payload, start_date, end_date)


def rows_to_csv(rows: list[dict[str, str]]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows({column: row.get(column, "") for column in CSV_COLUMNS} for row in rows)
    return output.getvalue()


def main() -> int:
    args = parse_args()
    try:
        rows = fetch_stock_fundamental_rows(
            args.symbol, args.start_date, args.end_date, args.user_agent
        )
    except (RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    sys.stdout.write(rows_to_csv(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
