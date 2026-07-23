#!/usr/bin/env python3
"""Fetch TipRanks forecast pages and persist normalized analyst CSV data.

The fetch path tries an ordinary HTTP request and then installed headless
Chrome. TipRanks may block either path. In that case the command fails without
writing partial data so the caller can use the documented external-browser
fallback and persist equivalent normalized rows.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[2]
SUMMARY_DIR = ROOT / "data/stock/tipranks-analysts-summary"
ACTIVITY_DIR = ROOT / "data/stock/tipranks-analysts-activity"
SUMMARY_FIELDS = [
    "scrape_date",
    "ticker",
    "average_rating_90d",
    "average_forecast_price_90d",
    "average_forecast_upside_90d",
    "average_upside_30d",
    "average_rating_30d",
]
ACTIVITY_FIELDS = [
    "activity_date",
    "ticker",
    "analyst_name",
    "analyst_grade_1_to_5",
    "expert_firm",
    "price_target",
    "position",
    "upside_downside",
    "action",
]
RATING_WORDS = r"(?:Strong Buy|Moderate Buy|Hold|Moderate Sell|Strong Sell)"
ACTION_WORDS = r"(?:Initiated|Assigned|Reiterated|Upgraded|Downgraded)"
RATING_SCORES = {
    "strong buy": "5",
    "moderate buy": "4",
    "hold": "3",
    "moderate sell": "2",
    "strong sell": "1",
}


def fetch_html(ticker: str) -> str:
    url = "https://www.tipranks.com/stocks/{}/forecast".format(ticker.lower())
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
        )
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.ok and "Average Price Target" in response.text:
            return response.text
    except requests.RequestException:
        pass

    chrome = shutil.which("google-chrome") or shutil.which("chromium")
    if not chrome:
        raise RuntimeError("TipRanks HTTP fetch failed and no Chrome executable is installed")
    with tempfile.TemporaryDirectory(prefix="tradix-tipranks-") as profile:
        command = [
            chrome,
            "--headless=new",
            "--no-sandbox",
            "--disable-gpu",
            "--disable-dev-shm-usage",
            "--user-data-dir={}".format(profile),
            "--dump-dom",
            url,
        ]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60)
    if result.returncode or "Average Price Target" not in result.stdout:
        raise RuntimeError("TipRanks blocked or omitted the rendered forecast data")
    return result.stdout


def first_match(pattern: str, text: str) -> str:
    match = re.search(pattern, text, flags=re.I | re.S)
    return match.group(1).strip() if match else ""


def normalize_percent(value: str) -> str:
    value = value.replace("%", "").replace("▲", "").replace("▼", "").strip()
    try:
        return "{:.2f}".format(float(value))
    except ValueError:
        return ""


def normalize_price(value: str) -> str:
    value = value.replace("$", "").replace(",", "").strip()
    try:
        return "{:.2f}".format(float(value))
    except ValueError:
        return ""


def parse_summary(html: str, ticker: str, scrape_date: str) -> Dict[str, str]:
    text = " ".join(BeautifulSoup(html, "html.parser").stripped_strings)
    rating_label = first_match(r"Analyst Ratings\s*(" + RATING_WORDS[3:-1] + r")", text)
    rating = RATING_SCORES.get(rating_label.lower(), "")
    target = normalize_price(first_match(r"Average Price Target\s*\$?([\d,]+(?:\.\d+)?)", text))
    upside_match = re.search(r"\(([+-]?[\d.]+)%\s*(Upside|Downside)\)", text, flags=re.I)
    upside = ""
    if upside_match:
        number = float(upside_match.group(1))
        if upside_match.group(2).lower() == "downside" and number > 0:
            number = -number
        upside = "{:.2f}".format(number)
    return {
        "scrape_date": scrape_date,
        "ticker": ticker,
        "average_rating_90d": rating,
        "average_forecast_price_90d": target,
        "average_forecast_upside_90d": upside,
        "average_upside_30d": "",
        "average_rating_30d": "",
    }


def parse_activity(html: str, ticker: str) -> List[Dict[str, str]]:
    """Parse visible analyst cards.

    TipRanks does not always expose the analyst's 1-to-5 grade in forecast-card
    markup. Such grades remain blank rather than being inferred.
    """
    soup = BeautifulSoup(html, "html.parser")
    rows: List[Dict[str, str]] = []
    seen = set()
    pattern = re.compile(r"Analyst forecast on {}".format(re.escape(ticker)), re.I)
    for image in soup.find_all("img", alt=pattern):
        container = image.parent
        for _ in range(9):
            if container is None:
                break
            text = " ".join(container.stripped_strings)
            if re.search(r"\b\d{2}/\d{2}/\d{2}\b", text) and re.search(ACTION_WORDS, text, re.I):
                break
            container = container.parent
        if container is None:
            continue
        text = " ".join(container.stripped_strings)
        date_value = first_match(r"\b(\d{2}/\d{2}/\d{2})\b", text)
        action = first_match(r"\b(" + ACTION_WORDS[3:-1] + r")\b", text)
        position = first_match(r"\b(Buy|Hold|Sell)\b", text)
        price_target = first_match(r"(\$[\d,.]+(?:\s*→\s*\$[\d,.]+)?)", text)
        pct_match = re.search(r"([+-]?[\d.]+)%\s*(Upside|Downside)", text, re.I)
        pct = ""
        if pct_match:
            number = float(pct_match.group(1))
            if pct_match.group(2).lower() == "downside" and number > 0:
                number = -number
            pct = "{:.2f}".format(number)

        analyst_name = ""
        analyst_link = image.find_next("a")
        if analyst_link:
            analyst_name = " ".join(analyst_link.stripped_strings)
        alt = image.get("alt", "")
        firm = alt.split(" Analyst forecast", 1)[0].strip()
        try:
            activity_date = dt.datetime.strptime(date_value, "%m/%d/%y").date().isoformat()
        except ValueError:
            continue
        row = {
            "activity_date": activity_date,
            "ticker": ticker,
            "analyst_name": analyst_name,
            "analyst_grade_1_to_5": "",
            "expert_firm": firm,
            "price_target": price_target,
            "position": position,
            "upside_downside": pct,
            "action": action,
        }
        key = tuple(row[field] for field in ACTIVITY_FIELDS)
        if key not in seen:
            seen.add(key)
            rows.append(row)
    return rows


def read_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, fields: List[str], rows: Iterable[Dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def persist_activity(rows: List[Dict[str, str]]) -> None:
    by_ticker: Dict[str, List[Dict[str, str]]] = {}
    for row in rows:
        by_ticker.setdefault(row["ticker"], []).append(row)
    for ticker, additions in by_ticker.items():
        path = ACTIVITY_DIR / "{}.csv".format(ticker)
        combined = read_rows(path) + additions
        unique = {tuple(row.get(field, "") for field in ACTIVITY_FIELDS): row for row in combined}
        ordered = sorted(unique.values(), key=lambda row: (row["activity_date"], row["ticker"], row["analyst_name"]))
        write_rows(path, ACTIVITY_FIELDS, ordered)


def numeric_mean(values: Iterable[str]) -> str:
    numbers = []
    for value in values:
        try:
            numbers.append(float(value))
        except (TypeError, ValueError):
            continue
    return "{:.2f}".format(sum(numbers) / len(numbers)) if numbers else ""


def add_30d_averages(summary: Dict[str, str]) -> Dict[str, str]:
    end = dt.date.fromisoformat(summary["scrape_date"])
    start = end - dt.timedelta(days=29)
    activity = []
    for path in ACTIVITY_DIR.glob("*.csv"):
        activity.extend(read_rows(path))
    window = [
        row
        for row in activity
        if row.get("ticker") == summary["ticker"]
        and start <= dt.date.fromisoformat(row["activity_date"]) <= end
    ]
    summary["average_upside_30d"] = numeric_mean(row.get("upside_downside", "") for row in window)
    summary["average_rating_30d"] = numeric_mean(row.get("analyst_grade_1_to_5", "") for row in window)
    return summary


def persist_summary(rows: List[Dict[str, str]]) -> None:
    by_ticker: Dict[str, List[Dict[str, str]]] = {}
    for row in rows:
        by_ticker.setdefault(row["ticker"], []).append(row)
    for ticker, additions in by_ticker.items():
        path = SUMMARY_DIR / "{}.csv".format(ticker)
        combined = read_rows(path) + additions
        keyed = {(row["scrape_date"], row["ticker"]): row for row in combined}
        ordered = sorted(keyed.values(), key=lambda row: (row["scrape_date"], row["ticker"]))
        write_rows(path, SUMMARY_FIELDS, ordered)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("tickers", nargs="+")
    parser.add_argument("--scrape-date", default=dt.date.today().isoformat())
    args = parser.parse_args()
    summaries = []
    for raw_ticker in args.tickers:
        ticker = raw_ticker.upper()
        html = fetch_html(ticker)
        activity = parse_activity(html, ticker)
        persist_activity(activity)
        summaries.append(add_30d_averages(parse_summary(html, ticker, args.scrape_date)))
        print("{}: persisted {} analyst activity rows".format(ticker, len(activity)))
    persist_summary(summaries)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
