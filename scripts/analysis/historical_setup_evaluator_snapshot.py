#!/usr/bin/env python3
"""Reproducible point-in-time comparison of the repository's three setup rubrics."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import random
import sys
from pathlib import Path


def as_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def load_rows(root, ticker):
    rows = []
    for path in sorted(root.glob("*/{}.csv".format(ticker))):
        with path.open(newline="") as handle:
            rows.extend(csv.DictReader(handle))
    return sorted(
        (row for row in rows if as_float(row.get("adj_close")) is not None),
        key=lambda row: row["date"],
    )


def load_evaluator(path):
    spec = importlib.util.spec_from_file_location("snapshot_lower_risk", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def trailing(rows, date):
    return [row for row in rows if row["date"] <= date]


def rsi(closes, window=14):
    if len(closes) <= window:
        return None
    changes = [closes[i] - closes[i - 1] for i in range(len(closes) - window, len(closes))]
    gain = sum(max(change, 0.0) for change in changes) / window
    loss = sum(max(-change, 0.0) for change in changes) / window
    if loss == 0:
        return 100.0
    return 100.0 - 100.0 / (1.0 + gain / loss)


def average(values):
    values = [value for value in values if value is not None]
    return sum(values) / len(values) if values else None


def percentile(values, value):
    return sum(candidate <= value for candidate in values) / len(values) if values else 0.0


def nearby_support(row, rows):
    price = as_float(row["adj_close"])
    candidates = [
        as_float(row.get("sma_20")),
        as_float(row.get("sma_50")),
        as_float(row.get("sma_150")),
        min(as_float(item["adj_low"]) for item in rows[-63:] if as_float(item.get("adj_low")) is not None),
    ]
    below = [level for level in candidates if level and level <= price * 1.03]
    return max(below) if below else None


def volume_ratio(rows):
    recent = average([as_float(row.get("volume")) for row in rows[-20:]])
    prior = average([as_float(row.get("volume")) for row in rows[-40:-20]])
    return recent / prior if recent is not None and prior else None


def qualitative_score(rows):
    row = rows[-1]
    price = as_float(row["adj_close"])
    support = nearby_support(row, rows)
    distance = abs(price / support - 1.0) if support else 1.0
    proximity = 45.0 * max(0.0, 1.0 - distance / 0.10)
    ret21 = as_float(row.get("ret_21"))
    ret126 = as_float(row.get("ret_126"))
    value_rsi = rsi([as_float(item["adj_close"]) for item in rows])
    pullback = 0.0
    pullback += 10.0 if ret21 is not None and -0.15 <= ret21 <= 0.02 else 0.0
    pullback += 10.0 if ret126 is not None and ret126 > 0 else 0.0
    pullback += 10.0 if value_rsi is not None and 40 <= value_rsi <= 60 else 0.0
    volume = volume_ratio(rows)
    volume_points = 10.0 if volume is not None and volume < 0.9 else (5.0 if volume is not None and volume < 1.0 else 0.0)
    # The archived rubric assigns importance to analyst revisions but supplies no
    # formula. Historical analyst observations are unavailable, so those 15 points
    # remain zero rather than being fabricated.
    return round(proximity + pullback + volume_points, 4), {
        "support": support,
        "support_distance_pct": distance * 100,
        "rsi14": value_rsi,
        "volume_ratio_20vprior20": volume,
        "analyst_points": 0,
    }


def quantitative_score(rows, spy_row, rs_percentile):
    row = rows[-1]
    price = as_float(row["adj_close"])
    sma50 = as_float(row.get("sma_50"))
    sma150 = as_float(row.get("sma_150"))
    prior150 = as_float(rows[-22].get("sma_150")) if len(rows) >= 22 else None
    trend = 5.0 * sum(
        [
            bool(sma150 and price > sma150),
            bool(sma150 and prior150 and sma150 > prior150),
            bool(sma50 and price > sma50),
            bool(sma50 and sma150 and sma50 > sma150),
        ]
    )
    relative = 0.0
    for field in ("ret_63", "ret_126", "ret_252"):
        stock_ret = as_float(row.get(field))
        spy_ret = as_float(spy_row.get(field))
        if stock_ret is not None and spy_ret is not None and stock_ret > spy_ret:
            relative += 4.0
    relative += 8.0 * rs_percentile
    support = nearby_support(row, rows)
    distance = abs(price / support - 1.0) if support else 1.0
    value_rsi = rsi([as_float(item["adj_close"]) for item in rows])
    volume = volume_ratio(rows)
    pullback = 5.0 * sum(
        [
            bool(distance <= 0.05),
            bool(value_rsi is not None and 40 <= value_rsi <= 60),
            bool(volume is not None and volume < 1.0),
        ]
    )
    recent_high = max(as_float(item["adj_high"]) for item in rows[-126:] if as_float(item.get("adj_high")) is not None)
    risk = price - support if support else None
    reward = recent_high - price
    rr = reward / risk if risk and risk > 0 else None
    geometry = (5.0 if support and distance <= 0.06 else 0.0)
    geometry += 10.0 if rr is not None and rr >= 3 else (7.0 if rr is not None and rr >= 2 else (3.0 if rr is not None and rr >= 1 else 0.0))
    # Historical analyst/estimate and fundamental data are absent. Their two
    # 15-point components remain zero for every ticker.
    score = trend + relative + pullback + geometry
    return round(score, 4), {
        "trend": trend,
        "relative_strength": relative,
        "pullback": pullback,
        "risk_reward_geometry": geometry,
        "rsi14": value_rsi,
        "reward_risk": rr,
        "analyst_revision_points": 0,
        "fundamental_points": 0,
    }


def row_on_or_before(rows, date):
    eligible = [row for row in rows if row["date"] <= date]
    return eligible[-1] if eligible else None


def cumulative_lows(rows, start_date, end_date):
    eligible = [
        row for row in rows
        if start_date <= row["date"] <= end_date
        and as_float(row.get("adj_close")) is not None
        and as_float(row.get("adj_low")) is not None
    ]
    if not eligible:
        return None
    closing_low_row = min(eligible, key=lambda row: as_float(row["adj_close"]))
    intraday_low_row = min(eligible, key=lambda row: as_float(row["adj_low"]))
    return {
        "lowest_close": as_float(closing_low_row["adj_close"]),
        "lowest_close_date": closing_low_row["date"],
        "lowest_intraday": as_float(intraday_low_row["adj_low"]),
        "lowest_intraday_date": intraday_low_row["date"],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--constituents", type=Path, required=True)
    parser.add_argument("--decision-date", default="2026-01-23")
    parser.add_argument("--seed", type=int, default=20260723)
    parser.add_argument("--sample-size", type=int, default=100)
    parser.add_argument("--features", type=Path, default=Path("data/stock/features/daily"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    evaluator_module = load_evaluator(Path("stages/setup-evaluators/lower_risk_swing_entry.py"))
    with args.constituents.open(newline="") as handle:
        constituents = [row["Symbol"].replace(".", "-") for row in csv.DictReader(handle)]
    available = {path.stem for path in (args.features / "2026").glob("*.csv")}
    rows_by_ticker = {}
    eligible = []
    for ticker in sorted(set(constituents) & available):
        rows = load_rows(args.features, ticker)
        decision_rows = trailing(rows, args.decision_date)
        if len(decision_rows) >= 252 and rows[-1]["date"] >= "2026-07-17":
            rows_by_ticker[ticker] = rows
            eligible.append(ticker)
    sampled = sorted(random.Random(args.seed).sample(eligible, args.sample_size))

    spy_rows = trailing(load_rows(args.features, "SPY"), args.decision_date)
    spy_row = spy_rows[-1]
    relative_126 = {
        ticker: as_float(trailing(rows_by_ticker[ticker], args.decision_date)[-1].get("ret_126"))
        - as_float(spy_row.get("ret_126"))
        for ticker in sampled
    }
    rs_values = list(relative_126.values())
    records = []
    lower_setups = []
    for ticker in sampled:
        decision_rows = trailing(rows_by_ticker[ticker], args.decision_date)
        lower_setups.append(evaluator_module.LowerRiskSwingEntryEvaluator.construct_setup(ticker, decision_rows))
        qual_score, qual_details = qualitative_score(decision_rows)
        quant_score, quant_details = quantitative_score(
            decision_rows, spy_row, percentile(rs_values, relative_126[ticker])
        )
        records.append({
            "ticker": ticker,
            "qualitative_score": qual_score,
            "qualitative_details": qual_details,
            "quantitative_score": quant_score,
            "quantitative_details": quant_details,
        })
    lower = evaluator_module.LowerRiskSwingEntryEvaluator.score_setups(lower_setups)
    lower_by_ticker = {
        item.setup.ticker: {
            "score": item.evaluation.setup_score,
            "evidence_score": item.evaluation.evidence_score,
            "status": item.evaluation.setup_status,
            "reward_risk": item.setup.reward_risk,
            "breakdown": item.evaluation.setup_score_breakdown,
        }
        for item in lower
    }
    for record in records:
        record["lower_risk"] = lower_by_ticker[record["ticker"]]

    winners = {
        "lower_risk_swing_entry": max(records, key=lambda item: (
            item["lower_risk"]["score"],
            item["lower_risk"]["evidence_score"],
            item["lower_risk"]["reward_risk"] or -1,
            item["ticker"],
        ))["ticker"],
        "qualitative_pullback_buy_zone": max(records, key=lambda item: (
            item["qualitative_score"], item["ticker"]
        ))["ticker"],
        "quantitative_swing_score": max(records, key=lambda item: (
            item["quantitative_score"], item["ticker"]
        ))["ticker"],
    }
    checkpoints = [
        ("6_months_ago", "2026-01-23"),
        ("5_months_ago", "2026-02-23"),
        ("4_months_ago", "2026-03-23"),
        ("3_months_ago", "2026-04-23"),
        ("2_months_ago", "2026-05-23"),
        ("1_month_ago", "2026-06-23"),
        ("current", "9999-12-31"),
    ]
    prices = {}
    for evaluator_id, ticker in winners.items():
        ticker_rows = rows_by_ticker[ticker]
        prices[evaluator_id] = {}
        base = as_float(row_on_or_before(ticker_rows, checkpoints[0][1])["adj_close"])
        for label, date in checkpoints:
            row = row_on_or_before(ticker_rows, date)
            value = as_float(row["adj_close"])
            lows = cumulative_lows(ticker_rows, checkpoints[0][1], row["date"])
            prices[evaluator_id][label] = {
                "requested_date": date,
                "actual_date": row["date"],
                "adj_close": value,
                "return_from_base_pct": (value / base - 1.0) * 100.0,
                **lows,
                "lowest_close_return_from_base_pct": (lows["lowest_close"] / base - 1.0) * 100.0,
                "lowest_intraday_return_from_base_pct": (lows["lowest_intraday"] / base - 1.0) * 100.0,
            }

    args.output.mkdir(parents=True, exist_ok=True)
    payload = {
        "decision_date": args.decision_date,
        "seed": args.seed,
        "eligible_count": len(eligible),
        "sample_size": len(sampled),
        "sampled_tickers": sampled,
        "winners": winners,
        "prices": prices,
        "records": sorted(records, key=lambda item: item["ticker"]),
        "limitations": [
            "Current S&P 500 membership creates survivorship/current-universe bias.",
            "Archived qualitative and quantitative rubrics have no executable formulas; deterministic adapters are documented in this script.",
            "Historical analyst, estimate-revision, and fundamental inputs were unavailable and scored zero, not fabricated.",
            "Prices are adjusted closes on the last trading session on or before each checkpoint.",
        ],
    }
    with (args.output / "results.json").open("w") as handle:
        json.dump(payload, handle, indent=2, allow_nan=False)
        handle.write("\n")
    with (args.output / "sample.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["ticker"])
        writer.writerows([[ticker] for ticker in sampled])
    print(json.dumps({key: payload[key] for key in ("decision_date", "seed", "eligible_count", "sample_size", "winners", "prices")}, indent=2))


if __name__ == "__main__":
    main()
