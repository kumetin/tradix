#!/usr/bin/env python3
"""Fetch historical OHLCV bars and write them as CSV.

The implementation intentionally uses only Python's standard library so it can
run in this repository without installing market-data packages.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import os
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Iterable


YAHOO_CHART_URLS = (
    "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
    "https://query2.finance.yahoo.com/v8/finance/chart/{symbol}",
)
TWELVE_DATA_URL = "https://api.twelvedata.com/time_series"

BAR_SIZE_ALIASES = {
    "1min": "1m",
    "2min": "2m",
    "5min": "5m",
    "15min": "15m",
    "30min": "30m",
    "60min": "60m",
    "90min": "90m",
    "1hour": "1h",
    "1h": "1h",
    "1day": "1d",
    "daily": "1d",
    "1week": "1wk",
    "weekly": "1wk",
    "1month": "1mo",
    "monthly": "1mo",
    "3month": "3mo",
    "quarterly": "3mo",
}

YAHOO_INTERVALS = {
    "1m",
    "2m",
    "5m",
    "15m",
    "30m",
    "60m",
    "90m",
    "1h",
    "1d",
    "5d",
    "1wk",
    "1mo",
    "3mo",
}

CSV_COLUMNS = [
    "symbol",
    "datetime",
    "date",
    "bar_size",
    "open",
    "high",
    "low",
    "close",
    "adj_close",
    "volume",
    "currency",
    "exchange_timezone",
    "source",
]

YAHOO_SOURCE = "yahoo_finance_chart"
TWELVE_DATA_SOURCE = "twelve_data_time_series"


def fetch_historical_csv(
    symbol: str,
    fromDate: str,
    toDate: str,
    barSize: str,
) -> str:
    """Return historical bars for ``symbol`` as CSV text.

    Args:
        symbol: Market symbol as understood by Yahoo Finance, for example
            ``AAPL`` or ``SPY``.
        fromDate: Start date or datetime. Examples: ``2026-01-01`` or
            ``2026-01-01T09:30:00-05:00``.
        toDate: End date or datetime. Date-only values are treated as inclusive
            through the end of that UTC day.
        barSize: Yahoo interval or common alias, for example ``1d``, ``1h``,
            ``15m``, ``daily``.
    """

    rows = fetch_historical_rows(symbol, fromDate, toDate, barSize)
    return rows_to_csv(rows)


def fetch_historical_rows(
    symbol: str,
    fromDate: str,
    toDate: str,
    barSize: str,
) -> list[dict[str, Any]]:
    interval = normalize_bar_size(barSize)
    period1 = parse_datetime(fromDate, inclusive_end=False)
    period2 = parse_datetime(toDate, inclusive_end=True)

    if period2 <= period1:
        raise ValueError("toDate must be after fromDate")

    try:
        return fetch_yahoo_rows(symbol, interval, period1, period2)
    except RuntimeError as exc:
        twelve_data_interval = to_twelve_data_interval(interval)
        if twelve_data_interval is None:
            raise
        return fetch_twelve_data_rows(
            symbol,
            twelve_data_interval,
            interval,
            period1,
            period2,
            exc,
        )


def fetch_yahoo_payload(symbol: str, query: str) -> dict[str, Any]:
    headers = {"User-Agent": "Mozilla/5.0"}
    last_error = None

    for template in YAHOO_CHART_URLS:
        url = f"{template.format(symbol=urllib.parse.quote(symbol.upper()))}?{query}"
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            last_error = RuntimeError(
                f"Yahoo Finance request failed with HTTP {exc.code}: {body}"
            )
        except urllib.error.URLError as exc:
            last_error = RuntimeError(f"Yahoo Finance request failed: {exc.reason}")

    if last_error is None:
        raise RuntimeError("Yahoo Finance request failed")
    raise last_error


def fetch_yahoo_rows(
    symbol: str,
    interval: str,
    period1: dt.datetime,
    period2: dt.datetime,
) -> list[dict[str, Any]]:
    query = urllib.parse.urlencode(
        {
            "period1": int(period1.timestamp()),
            "period2": int(period2.timestamp()),
            "interval": interval,
            "includePrePost": "false",
            "events": "history",
        }
    )

    payload = fetch_yahoo_payload(symbol, query)
    return parse_yahoo_payload(payload, symbol, interval)


def parse_yahoo_payload(
    payload: dict[str, Any], symbol: str, interval: str
) -> list[dict[str, Any]]:
    """Normalize a Yahoo chart payload into canonical price rows."""

    chart = payload.get("chart", {})
    error = chart.get("error")
    if error:
        description = error.get("description") or error.get("code") or error
        raise RuntimeError(f"Yahoo Finance returned an error: {description}")

    results = chart.get("result") or []
    if not results:
        return []

    result = results[0]
    timestamps = result.get("timestamp") or []
    indicators = result.get("indicators", {})
    quote = first(indicators.get("quote")) or {}
    adjclose = first(indicators.get("adjclose")) or {}
    meta = result.get("meta", {})

    rows: list[dict[str, Any]] = []
    for index, timestamp in enumerate(timestamps):
        instant = dt.datetime.fromtimestamp(timestamp, tz=dt.timezone.utc)
        rows.append(
            {
                "symbol": meta.get("symbol") or symbol.upper(),
                "datetime": instant.isoformat(),
                "date": instant.date().isoformat(),
                "bar_size": interval,
                "open": value_at(quote.get("open"), index),
                "high": value_at(quote.get("high"), index),
                "low": value_at(quote.get("low"), index),
                "close": value_at(quote.get("close"), index),
                "adj_close": value_at(adjclose.get("adjclose"), index),
                "volume": value_at(quote.get("volume"), index),
                "currency": meta.get("currency"),
                "exchange_timezone": meta.get("exchangeTimezoneName"),
                "source": YAHOO_SOURCE,
            }
        )

    return rows


def fetch_twelve_data_rows(
    symbol: str,
    twelve_data_interval: str,
    bar_size: str,
    period1: dt.datetime,
    period2: dt.datetime,
    yahoo_error: RuntimeError,
) -> list[dict[str, Any]]:
    query = urllib.parse.urlencode(
        {
            "symbol": symbol.upper(),
            "interval": twelve_data_interval,
            "start_date": period1.date().isoformat(),
            "end_date": (period2 - dt.timedelta(days=1)).date().isoformat(),
            "outputsize": 5000,
            "format": "JSON",
            "apikey": os.environ.get("TWELVEDATA_API_KEY", "demo"),
        }
    )
    request = urllib.request.Request(
        f"{TWELVE_DATA_URL}?{query}",
        headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Yahoo Finance failed ({yahoo_error}); Twelve Data failed with "
            f"HTTP {exc.code}: {body}"
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Yahoo Finance failed ({yahoo_error}); Twelve Data failed: {exc.reason}"
        ) from exc

    if payload.get("status") == "error":
        raise RuntimeError(
            f"Yahoo Finance failed ({yahoo_error}); Twelve Data returned an error: "
            f"{payload.get('message') or payload}"
        )

    return parse_twelve_data_payload(payload, symbol, bar_size)


def parse_twelve_data_payload(
    payload: dict[str, Any], symbol: str, bar_size: str
) -> list[dict[str, Any]]:
    """Normalize a Twelve Data time-series payload into canonical rows."""

    values = payload.get("values") or []
    meta = payload.get("meta") or {}
    rows: list[dict[str, Any]] = []
    for raw in reversed(values):
        instant = parse_datetime(raw["datetime"], inclusive_end=False)
        rows.append(
            {
                "symbol": meta.get("symbol") or symbol.upper(),
                "datetime": instant.isoformat(),
                "date": instant.date().isoformat(),
                "bar_size": bar_size,
                "open": to_float(raw.get("open")),
                "high": to_float(raw.get("high")),
                "low": to_float(raw.get("low")),
                "close": to_float(raw.get("close")),
                "adj_close": to_float(raw.get("close")),
                "volume": to_int(raw.get("volume")),
                "currency": meta.get("currency"),
                "exchange_timezone": meta.get("exchange_timezone"),
                "source": TWELVE_DATA_SOURCE,
            }
        )

    return rows


def rows_to_csv(rows: list[dict[str, Any]]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({column: format_csv_value(row.get(column)) for column in CSV_COLUMNS})
    return output.getvalue()


def parse_datetime(value: str, inclusive_end: bool) -> dt.datetime:
    is_date_only = len(value) == 10 and value[4] == "-" and value[7] == "-"

    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"invalid date/datetime: {value!r}") from exc

    if isinstance(parsed, dt.datetime):
        result = parsed
    else:
        result = dt.datetime.combine(parsed, dt.time.min)

    if result.tzinfo is None:
        result = result.replace(tzinfo=dt.timezone.utc)
    else:
        result = result.astimezone(dt.timezone.utc)

    if inclusive_end and is_date_only:
        result += dt.timedelta(days=1)

    return result


def normalize_bar_size(value: str) -> str:
    normalized = value.strip().lower().replace(" ", "")
    normalized = BAR_SIZE_ALIASES.get(normalized, normalized)

    if normalized not in YAHOO_INTERVALS:
        supported = ", ".join(sorted(YAHOO_INTERVALS | set(BAR_SIZE_ALIASES)))
        raise ValueError(f"unsupported barSize {value!r}; supported values: {supported}")

    return normalized


def first(values: list[Any] | None) -> Any:
    if isinstance(values, list) and values:
        return values[0]
    return None


def value_at(values: list[Any] | None, index: int) -> Any:
    if isinstance(values, list) and index < len(values):
        return values[index]
    return None


def to_twelve_data_interval(interval: str) -> str | None:
    return {
        "1m": "1min",
        "5m": "5min",
        "15m": "15min",
        "30m": "30min",
        "1h": "1h",
        "1d": "1day",
        "1wk": "1week",
        "1mo": "1month",
    }.get(interval)


def parse_number(value: Any) -> float | int | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return value
    text = str(value)
    if "." in text:
        return float(text)
    return int(text)


def to_float(value: Any) -> float | None:
    parsed = parse_number(value)
    return None if parsed is None else float(parsed)


def to_int(value: Any) -> int | None:
    parsed = parse_number(value)
    return None if parsed is None else int(parsed)


def format_csv_value(value: Any) -> str:
    return "" if value is None else str(value)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch historical OHLCV bars and write CSV to stdout."
    )
    parser.add_argument("symbol")
    parser.add_argument("fromDate")
    parser.add_argument("toDate")
    parser.add_argument("barSize")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        sys.stdout.write(
            fetch_historical_csv(
                symbol=args.symbol,
                fromDate=args.fromDate,
                toDate=args.toDate,
                barSize=args.barSize,
            )
        )
    except (RuntimeError, ValueError) as exc:
        print(f"fetch_stock_prices.py: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
