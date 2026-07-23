#!/usr/bin/env python3
"""Diagnose point-in-time features associated with failed +5.21% exits."""

from __future__ import annotations

import csv
import json
import statistics
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
import historical_setup_evaluator_snapshot as snapshot


ARTIFACT_ROOT = (
    ROOT
    / "artifacts/stock/backtests/strategies/technical-resistance-runner/robustness"
)
OUTPUT = ARTIFACT_ROOT / "filter-discovery"
DISCOVERY_UNIVERSES = (1, 2, 3)
DIAGNOSTIC_UNIVERSES = (4, 5)


def read_csv(path):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def ratio(value, base):
    return (value / base - 1.0) * 100.0 if value is not None and base else None


def observation_rows(universe_number):
    directory = ARTIFACT_ROOT / "universe-{}".format(universe_number) / "full_at_5_21"
    predictions = read_csv(directory / "predictions.csv")
    trades = read_csv(directory / "trades.csv")
    entries = {
        (row["entry_date"], row["ticker"]): row
        for row in predictions
        if row["action"] == "enter"
    }
    histories = {}
    spy = {
        row["date"]: row
        for row in snapshot.load_rows(ROOT / "data/stock/features/daily", "SPY")
    }
    observations = []
    for trade in trades:
        key = (trade["entry_date"], trade["ticker"])
        prediction = entries.get(key)
        if prediction is None:
            continue
        ticker = trade["ticker"]
        histories.setdefault(
            ticker,
            {row["date"]: row for row in snapshot.load_rows(ROOT / "data/stock/features/daily", ticker)},
        )
        feature = histories[ticker].get(prediction["decision_date"])
        market = spy.get(prediction["decision_date"])
        if feature is None or market is None:
            continue
        components = json.loads(prediction["score_components"])
        price = snapshot.as_float(feature["adj_close"])
        support = float(prediction["support"])
        target = float(prediction["target"])
        row = {
            "universe": universe_number,
            "decision_date": prediction["decision_date"],
            "entry_date": trade["entry_date"],
            "ticker": ticker,
            "profitable": float(trade["return_pct"]) > 0,
            "target_hit": bool(trade["first_target_date"]),
            "return_pct": float(trade["return_pct"]),
            "score": float(prediction["score"]),
            "score_pullback": float(components["pullback"]),
            "score_relative_strength": float(components["relative_strength"]),
            "score_risk_geometry": float(components["risk_reward_geometry"]),
            "score_trend": float(components["trend"]),
            "reward_risk": float(components["reward_risk"]),
            "rsi14": float(components["rsi14"]),
            "price_vs_sma20_pct": ratio(price, snapshot.as_float(feature["sma_20"])),
            "price_vs_sma50_pct": ratio(price, snapshot.as_float(feature["sma_50"])),
            "price_vs_sma150_pct": ratio(price, snapshot.as_float(feature["sma_150"])),
            "distance_52w_high_pct": ratio(price, snapshot.as_float(feature["high_252"])),
            "drawdown_52w_pct": snapshot.as_float(feature["dd_252"]) * 100.0,
            "ret_63_pct": snapshot.as_float(feature["ret_63"]) * 100.0,
            "ret_126_pct": snapshot.as_float(feature["ret_126"]) * 100.0,
            "ret_252_pct": snapshot.as_float(feature["ret_252"]) * 100.0,
            "target_upside_pct": ratio(target, price),
            "support_distance_pct": ratio(price, support),
            "eligible_fraction_pct": float(prediction["eligible_count"]) / 50.0 * 100.0,
            "spy_price_vs_sma50_pct": ratio(
                snapshot.as_float(market["adj_close"]),
                snapshot.as_float(market["sma_50"]),
            ),
            "spy_price_vs_sma150_pct": ratio(
                snapshot.as_float(market["adj_close"]),
                snapshot.as_float(market["sma_150"]),
            ),
            "spy_ret_63_pct": snapshot.as_float(market["ret_63"]) * 100.0,
            "spy_ret_126_pct": snapshot.as_float(market["ret_126"]) * 100.0,
            "spy_drawdown_52w_pct": snapshot.as_float(market["dd_252"]) * 100.0,
        }
        observations.append(row)
    return observations


def mean(rows, field):
    values = [row[field] for row in rows if row[field] is not None]
    return statistics.mean(values) if values else None


def feature_comparison(rows):
    winners = [row for row in rows if row["profitable"]]
    losers = [row for row in rows if not row["profitable"]]
    fields = [
        key
        for key in rows[0]
        if key not in {"universe", "decision_date", "entry_date", "ticker", "profitable", "target_hit", "return_pct"}
    ]
    result = []
    for field in fields:
        winner_mean = mean(winners, field)
        loser_mean = mean(losers, field)
        result.append(
            {
                "feature": field,
                "winner_mean": winner_mean,
                "loser_mean": loser_mean,
                "winner_minus_loser": winner_mean - loser_mean,
            }
        )
    return result


def threshold_search(rows):
    fields = [
        key
        for key in rows[0]
        if key not in {"universe", "decision_date", "entry_date", "ticker", "profitable", "target_hit", "return_pct"}
    ]
    candidates = []
    for field in fields:
        values = sorted(set(row[field] for row in rows if row[field] is not None))
        for threshold in values[1:-1]:
            for direction in ("min", "max"):
                kept = [
                    row
                    for row in rows
                    if row[field] is not None
                    and ((row[field] >= threshold) if direction == "min" else (row[field] <= threshold))
                ]
                retention = len(kept) / len(rows)
                if retention < 0.60:
                    continue
                candidates.append(
                    {
                        "feature": field,
                        "direction": direction,
                        "threshold": threshold,
                        "retention": retention,
                        "trades": len(kept),
                        "win_rate": sum(row["profitable"] for row in kept) / len(kept),
                        "mean_return_pct": mean(kept, "return_pct"),
                    }
                )
    candidates.sort(key=lambda row: (-row["mean_return_pct"], -row["win_rate"], -row["retention"]))
    return candidates


def write_csv(path, rows):
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    discovery = []
    diagnostic = []
    for universe in DISCOVERY_UNIVERSES:
        discovery.extend(observation_rows(universe))
    for universe in DIAGNOSTIC_UNIVERSES:
        diagnostic.extend(observation_rows(universe))
    comparisons = feature_comparison(discovery)
    thresholds = threshold_search(discovery)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    write_csv(OUTPUT / "discovery-observations.csv", discovery)
    write_csv(OUTPUT / "diagnostic-observations.csv", diagnostic)
    write_csv(OUTPUT / "feature-comparison.csv", comparisons)
    write_csv(OUTPUT / "univariate-thresholds.csv", thresholds)
    payload = {
        "discovery_universes": DISCOVERY_UNIVERSES,
        "diagnostic_universes": DIAGNOSTIC_UNIVERSES,
        "discovery_trades": len(discovery),
        "discovery_win_rate": sum(row["profitable"] for row in discovery) / len(discovery),
        "top_thresholds": thresholds[:20],
    }
    (OUTPUT / "results.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
