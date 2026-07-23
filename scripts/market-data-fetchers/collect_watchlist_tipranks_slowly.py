#!/usr/bin/env python3
"""Slow, resumable TipRanks collection for every repository watchlist ticker."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import importlib.util
import json
import re
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FETCHER_PATH = Path(__file__).with_name("fetch_tipranks_analysts.py")
STATE_PATH = ROOT / "artifacts/stock/tipranks-collection/state.json"
LOG_PATH = ROOT / "artifacts/stock/tipranks-collection/collector.log"


def load_fetcher():
    spec = importlib.util.spec_from_file_location("tradix_tipranks_fetcher", str(FETCHER_PATH))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


FETCHER = load_fetcher()


def discover_tickers():
    tickers = set()
    for path in sorted((ROOT / "watchlists").glob("*")):
        if not path.is_file() or path.name == "README.md":
            continue
        for raw in path.read_text().splitlines():
            line = raw.strip()
            if "," in line:
                for candidate in line.split(":")[-1].split(","):
                    candidate = candidate.strip().upper()
                    if re.fullmatch(r"[A-Z0-9.]+", candidate):
                        tickers.add(candidate)
            match = re.match(r"-\s+([A-Z0-9.]+)\b", line, flags=re.I)
            if match:
                tickers.add(match.group(1).upper())
    return sorted(tickers)


def load_state():
    if not STATE_PATH.exists():
        return {"completed": {}, "failures": {}}
    try:
        return json.loads(STATE_PATH.read_text())
    except (ValueError, OSError):
        return {"completed": {}, "failures": {}}


def atomic_text(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(value)
    temporary.replace(path)


def save_state(state):
    atomic_text(STATE_PATH, json.dumps(state, indent=2, sort_keys=True) + "\n")


def log(message):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.now().isoformat(timespec="seconds")
    with LOG_PATH.open("a") as handle:
        handle.write("{} {}\n".format(timestamp, message))
    print(message, flush=True)


def summary_complete_today(ticker, scrape_date):
    path = FETCHER.SUMMARY_DIR / "{}.csv".format(ticker)
    if not path.exists():
        return False
    with path.open(newline="") as handle:
        return any(
            row.get("scrape_date") == scrape_date and row.get("ticker") == ticker
            for row in csv.DictReader(handle)
        )


def activity_key(row):
    return tuple(row.get(field, "") for field in FETCHER.ACTIVITY_FIELDS)


def new_activity_prefix(ticker, displayed_rows):
    """Keep newest cards only, stopping at the first persisted activity row."""
    path = FETCHER.ACTIVITY_DIR / "{}.csv".format(ticker)
    persisted = {activity_key(row) for row in FETCHER.read_rows(path)}
    additions = []
    for row in displayed_rows:
        if activity_key(row) in persisted:
            break
        additions.append(row)
    return additions


def collect_one(ticker, scrape_date):
    page = FETCHER.fetch_html(ticker)
    displayed_activity = FETCHER.parse_activity(page, ticker)
    activity = new_activity_prefix(ticker, displayed_activity)
    summary = FETCHER.parse_summary(page, ticker, scrape_date)
    if not summary.get("average_rating_90d") and not summary.get("average_forecast_price_90d"):
        raise RuntimeError("forecast page omitted usable consensus fields")
    FETCHER.persist_activity(activity)
    FETCHER.persist_summary([FETCHER.add_30d_averages(summary)])
    return len(activity), len(displayed_activity)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--delay-seconds", type=float, default=90.0)
    parser.add_argument("--max-tickers", type=int)
    parser.add_argument("--scrape-date", default=dt.date.today().isoformat())
    args = parser.parse_args()

    state = load_state()
    queue = discover_tickers()
    attempted = 0
    log("queue-start tickers={} scrape_date={}".format(len(queue), args.scrape_date))
    for ticker in queue:
        if summary_complete_today(ticker, args.scrape_date):
            state["completed"][ticker] = args.scrape_date
            save_state(state)
            continue
        if args.max_tickers is not None and attempted >= args.max_tickers:
            break
        attempted += 1
        try:
            count, displayed_count = collect_one(ticker, args.scrape_date)
            state["completed"][ticker] = args.scrape_date
            state["failures"].pop(ticker, None)
            log("{} success new_activity_rows={} displayed_rows={}".format(
                ticker, count, displayed_count))
        except Exception as error:
            state["failures"][ticker] = {
                "date": args.scrape_date,
                "error": str(error),
            }
            log("{} failure {}".format(ticker, error))
        save_state(state)
        if args.delay_seconds > 0:
            time.sleep(args.delay_seconds)
    log("queue-stop attempted={} completed_today={} failures={}".format(
        attempted,
        sum(value == args.scrape_date for value in state["completed"].values()),
        len(state["failures"]),
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
