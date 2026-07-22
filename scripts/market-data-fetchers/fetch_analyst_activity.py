#!/usr/bin/env python3
"""Fetch analyst upgrade/downgrade activity and write it as CSV.

The implementation intentionally uses only Python's standard library so it can
run in this repository without installing market-data packages.

Free provider:
    MarketBeat stock forecast pages. These are public HTML pages and require no
    API key.

Optional provider:
    Finnhub ``/stock/upgrade-downgrade``. Set ``FINNHUB_API_KEY`` and pass
    ``--source finnhub``.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import html
import io
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


FINNHUB_URL = "https://finnhub.io/api/v1/stock/upgrade-downgrade"
MARKETBEAT_EXCHANGES = ("NYSE", "NASDAQ", "NYSEAMERICAN", "NYSEARCA", "OTCMKTS")

CSV_COLUMNS = [
    "symbol",
    "date",
    "datetime",
    "firm",
    "analyst",
    "from_grade",
    "to_grade",
    "from_price_target",
    "to_price_target",
    "action",
    "source",
    "source_url",
    "fetched_at_utc",
]


def fetch_analyst_activity_csv(
    symbol: str,
    fromDate: str,
    toDate: str,
    source: str = "marketbeat",
) -> str:
    """Return analyst activity for ``symbol`` as CSV text."""

    return rows_to_csv(fetch_analyst_activity_rows(symbol, fromDate, toDate, source))


def fetch_analyst_activity_rows(
    symbol: str,
    fromDate: str,
    toDate: str,
    source: str = "marketbeat",
) -> list[dict[str, Any]]:
    """Return normalized upgrade/downgrade rows for ``symbol``.

    Args:
        symbol: Market symbol, for example ``AAPL``.
        fromDate: Inclusive start date in ``YYYY-MM-DD`` form.
        toDate: Inclusive end date in ``YYYY-MM-DD`` form.
        source: ``marketbeat`` for free public HTML scraping, or ``finnhub`` if
            ``FINNHUB_API_KEY`` is configured.
    """

    symbol = symbol.upper()
    start = parse_date(fromDate)
    end = parse_date(toDate)
    if end < start:
        raise ValueError("toDate must be on or after fromDate")

    if source == "marketbeat":
        return fetch_marketbeat_rows(symbol, start, end)
    if source == "finnhub":
        return fetch_finnhub_rows(symbol, start, end)
    raise ValueError("source must be one of: marketbeat, finnhub")


def fetch_marketbeat_rows(
    symbol: str,
    start: dt.date,
    end: dt.date,
) -> list[dict[str, Any]]:
    url, payload = fetch_marketbeat_payload(symbol)
    fetched_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    rows = parse_marketbeat_rows(symbol, payload, url, fetched_at)
    rows = [row for row in rows if start.isoformat() <= row["date"] <= end.isoformat()]
    rows.sort(key=lambda row: (row["date"], row["firm"], row["analyst"], row["action"]))
    return rows


def fetch_marketbeat_payload(symbol: str) -> tuple[str, str]:
    errors = []
    for exchange in MARKETBEAT_EXCHANGES:
        url = f"https://www.marketbeat.com/stocks/{exchange}/{urllib.parse.quote(symbol)}/forecast/"
        try:
            payload = fetch_text(url)
        except RuntimeError as exc:
            errors.append(f"{exchange}: {exc}")
            continue
        if is_marketbeat_stock_forecast_page(symbol, payload):
            return url, payload
        errors.append(f"{exchange}: no forecast page")
    raise RuntimeError(f"MarketBeat forecast page not found for {symbol}: {'; '.join(errors)}")


def fetch_text(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(str(exc.reason)) from exc


def is_marketbeat_stock_forecast_page(symbol: str, payload: str) -> bool:
    lower = payload.lower()
    return (
        "stock forecast" in lower
        and "cphprimarycontent_cphtabcontent_ddlactiontaken" in lower
        and f"/{symbol.lower()}/" in lower
    )


def parse_marketbeat_rows(
    symbol: str,
    payload: str,
    source_url: str,
    fetched_at_utc: str,
) -> list[dict[str, Any]]:
    rows = []
    for tr in re.findall(r"<tr\b[^>]*>(.*?)</tr>", payload, flags=re.I | re.S):
        cells = table_cells(tr)
        if len(cells) < 6:
            continue
        action = cells[3]
        if action not in {
            "Upgrade",
            "Downgrade",
            "Initiated Coverage",
            "Boost Target",
            "Lower Target",
            "Lower Price Target",
            "Set Target",
            "Reiterated Rating",
        }:
            continue

        row_date = parse_marketbeat_date(cells[0])
        from_grade, to_grade = split_change(cells[4])
        from_target, to_target = split_change(cells[5])
        rows.append(
            {
                "symbol": symbol,
                "date": row_date.isoformat(),
                "datetime": dt.datetime.combine(row_date, dt.time(), tzinfo=dt.timezone.utc).isoformat(),
                "firm": clean_marketbeat_entity(cells[1]),
                "analyst": clean_marketbeat_entity(cells[2]),
                "from_grade": empty_na(from_grade),
                "to_grade": empty_na(to_grade),
                "from_price_target": empty_zero_price(from_target),
                "to_price_target": empty_zero_price(to_target),
                "action": normalize_marketbeat_action(action),
                "source": "marketbeat_stock_forecast",
                "source_url": source_url,
                "fetched_at_utc": fetched_at_utc,
            }
        )
    return rows


def table_cells(tr: str) -> list[str]:
    cells = []
    for attrs, body in re.findall(r"<td\b([^>]*)>(.*?)</td>", tr, flags=re.I | re.S):
        match = re.search(r'data-clean="([^"]*)"', attrs, flags=re.I)
        if match:
            value = html.unescape(match.group(1))
        else:
            value = html.unescape(re.sub(r"<[^>]+>", " ", body))
        cells.append(" ".join(value.split()))
    return cells


def parse_marketbeat_date(value: str) -> dt.date:
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    raise RuntimeError(f"Unexpected MarketBeat date: {value!r}")


def split_change(value: str) -> tuple[str, str]:
    if "|" in value:
        before, after = value.split("|", 1)
        return before.strip(), after.strip()
    return "", value.strip()


def clean_marketbeat_entity(value: str) -> str:
    value = value.split("|", 1)[0].strip()
    if value in {"", "Subscribe to All Access for Analyst Ratings"}:
        return ""
    return value


def empty_na(value: str) -> str:
    return "" if value in {"", "N/A", "|"} else value


def empty_zero_price(value: str) -> str:
    value = value.strip()
    return "" if value in {"", "0", "$0.00", "0.00"} else value


def normalize_marketbeat_action(action: str) -> str:
    mapping = {
        "Initiated Coverage": "init",
        "Boost Target": "raise_target",
        "Lower Target": "lower_target",
        "Lower Price Target": "lower_target",
        "Set Target": "set_target",
        "Reiterated Rating": "reiterate",
    }
    return mapping.get(action, action.lower())


def fetch_finnhub_rows(
    symbol: str,
    start: dt.date,
    end: dt.date,
) -> list[dict[str, Any]]:
    token = os.environ.get("FINNHUB_API_KEY")
    if not token:
        raise RuntimeError("FINNHUB_API_KEY is required when source=finnhub")

    payload = fetch_finnhub_payload(symbol, start.isoformat(), end.isoformat(), token)
    fetched_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    rows = [normalize_finnhub_row(symbol, raw, fetched_at) for raw in payload]
    rows = [row for row in rows if start.isoformat() <= row["date"] <= end.isoformat()]
    rows.sort(key=lambda row: (row["date"], row["firm"], row["to_grade"], row["from_grade"]))
    return rows


def fetch_finnhub_payload(
    symbol: str,
    from_date: str,
    to_date: str,
    token: str,
) -> list[dict[str, Any]]:
    query = urllib.parse.urlencode(
        {
            "symbol": symbol,
            "from": from_date,
            "to": to_date,
            "token": token,
        }
    )
    request = urllib.request.Request(
        f"{FINNHUB_URL}?{query}",
        headers={"User-Agent": "Tradix/1.0", "Accept": "application/json"},
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Finnhub request failed with HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Finnhub request failed: {exc.reason}") from exc

    if isinstance(payload, dict) and payload.get("error"):
        raise RuntimeError(f"Finnhub returned an error: {payload['error']}")
    if not isinstance(payload, list):
        raise RuntimeError(f"Finnhub returned unexpected payload: {payload!r}")
    return payload


def normalize_finnhub_row(
    requested_symbol: str,
    raw: dict[str, Any],
    fetched_at_utc: str,
) -> dict[str, Any]:
    grade_time = raw.get("gradeTime") or raw.get("date") or raw.get("datetime")
    instant = parse_provider_time(grade_time)
    return {
        "symbol": (raw.get("symbol") or requested_symbol).upper(),
        "date": instant.date().isoformat(),
        "datetime": instant.isoformat(),
        "firm": clean(raw.get("company")),
        "analyst": "",
        "from_grade": clean(raw.get("fromGrade")),
        "to_grade": clean(raw.get("toGrade")),
        "from_price_target": "",
        "to_price_target": "",
        "action": clean(raw.get("action")),
        "source": "finnhub_stock_upgrade_downgrade",
        "source_url": FINNHUB_URL,
        "fetched_at_utc": fetched_at_utc,
    }


def parse_provider_time(value: Any) -> dt.datetime:
    if isinstance(value, (int, float)):
        return dt.datetime.fromtimestamp(value, tz=dt.timezone.utc)
    if isinstance(value, str) and value:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        try:
            parsed = dt.datetime.fromisoformat(value)
        except ValueError:
            parsed_date = parse_date(value[:10])
            return dt.datetime.combine(parsed_date, dt.time(), tzinfo=dt.timezone.utc)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed.astimezone(dt.timezone.utc)
    raise RuntimeError(f"Missing analyst activity timestamp in provider row: {value!r}")


def parse_date(value: str) -> dt.date:
    try:
        return dt.date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Invalid date {value!r}; expected YYYY-MM-DD") from exc


def clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def rows_to_csv(rows: list[dict[str, Any]]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows({column: row.get(column, "") for column in CSV_COLUMNS} for row in rows)
    return buffer.getvalue()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("symbol")
    parser.add_argument("start_date")
    parser.add_argument("end_date")
    parser.add_argument(
        "--source",
        choices=("marketbeat", "finnhub"),
        default="marketbeat",
        help="Data source. marketbeat is free/public HTML and requires no key.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    sys.stdout.write(
        fetch_analyst_activity_csv(args.symbol, args.start_date, args.end_date, args.source)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
