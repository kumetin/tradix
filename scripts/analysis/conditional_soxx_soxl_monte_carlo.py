#!/usr/bin/env python3
"""Conditional SOXX path bootstrap with mechanical daily SOXL compounding."""

import argparse
import csv
import json
from pathlib import Path

import numpy as np


def load_prices(root, symbol):
    rows = []
    for path in sorted(root.glob(f"*/{symbol}.csv")):
        with path.open(newline="") as handle:
            rows.extend(csv.DictReader(handle))
    return {row["date"]: float(row["adj_close"]) for row in rows if row.get("adj_close")}


def weighted_block_paths(returns, horizon, count, recent, recent_weight, block, rng):
    starts = np.arange(len(returns) - block + 1)
    weights = np.ones(len(starts))
    weights[starts + block > len(returns) - recent] = recent_weight
    weights /= weights.sum()
    blocks = (horizon + block - 1) // block
    chosen = rng.choice(starts, size=(count, blocks), p=weights)
    offsets = np.arange(block)
    sampled = returns[chosen[..., None] + offsets]
    return sampled.reshape(count, blocks * block)[:, :horizon]


def summarize(values):
    q = np.quantile(values, [0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99])
    return dict(zip(["p01", "p05", "p25", "p50", "p75", "p95", "p99"], map(float, q)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prices", type=Path, default=Path("data/stock/prices/daily"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/stock/backtests/conditional-soxx-soxl-monte-carlo"))
    parser.add_argument("--paths", type=int, default=100_000)
    parser.add_argument("--history-days", type=int, default=756)
    parser.add_argument("--recent-days", type=int, default=90)
    parser.add_argument("--recent-weight", type=float, default=3.0)
    parser.add_argument("--block-days", type=int, default=5)
    parser.add_argument("--near-ath", type=float, default=0.02)
    parser.add_argument("--seed", type=int, default=20260723)
    args = parser.parse_args()

    soxx = load_prices(args.prices, "SOXX")
    soxl = load_prices(args.prices, "SOXL")
    dates = sorted(set(soxx) & set(soxl))
    soxx_px = np.array([soxx[d] for d in dates])
    soxl_px = np.array([soxl[d] for d in dates])
    soxx_ret = soxx_px[1:] / soxx_px[:-1] - 1
    soxl_ret = soxl_px[1:] / soxl_px[:-1] - 1

    history = min(args.history_days, len(soxx_ret))
    sample_ret = soxx_ret[-history:]
    # A robust empirical estimate of financing, expenses, tracking, and index mismatch.
    implied_cost = 3 * soxx_ret[-history:] - soxl_ret[-history:]
    lo, hi = np.quantile(implied_cost, [0.01, 0.99])
    daily_cost = float(implied_cost[(implied_cost >= lo) & (implied_cost <= hi)].mean())

    start_soxx = float(soxx_px[-1])
    start_soxl = float(soxl_px[-1])
    ath_soxx = float(soxx_px.max())
    ath_date = dates[int(soxx_px.argmax())]
    rng = np.random.default_rng(args.seed)
    results = []

    for label, horizon in [("3m", 63), ("4.5m", 95), ("6m", 126)]:
        paths = weighted_block_paths(sample_ret, horizon, args.paths, args.recent_days,
                                     args.recent_weight, args.block_days, rng)
        soxx_path = start_soxx * np.cumprod(1 + paths, axis=1)
        terminal = soxx_path[:, -1]
        touched = soxx_path.max(axis=1) >= ath_soxx
        finished_near = np.abs(terminal / ath_soxx - 1) <= args.near_ath
        retained = touched | finished_near
        soxl_path = start_soxl * np.cumprod(1 + 3 * paths - daily_cost, axis=1)
        soxl_terminal = soxl_path[retained, -1]
        result = {
            "horizon": label,
            "trading_days": horizon,
            "generated_paths": args.paths,
            "retained_paths": int(retained.sum()),
            "retention_rate": float(retained.mean()),
            "touch_rate": float(touched.mean()),
            "finish_near_rate": float(finished_near.mean()),
            "soxx_terminal_retained_median": float(np.median(terminal[retained])),
            "soxl_probability_profit": float(np.mean(soxl_terminal > start_soxl)),
            "soxl_probability_loss_25pct": float(np.mean(soxl_terminal <= start_soxl * .75)),
            "soxl_probability_gain_50pct": float(np.mean(soxl_terminal >= start_soxl * 1.5)),
            "soxl_terminal": summarize(soxl_terminal),
            "soxl_return": summarize(soxl_terminal / start_soxl - 1),
        }
        results.append(result)

    metadata = {
        "data_end": dates[-1], "history_observations": history,
        "history_start_return_date": dates[-history], "start_soxx": start_soxx,
        "start_soxl": start_soxl, "assumed_soxx_ath": ath_soxx,
        "ath_date": ath_date, "daily_cost": daily_cost,
        "simple_annualized_cost": daily_cost * 252,
        "recent_days": args.recent_days, "recent_weight": args.recent_weight,
        "block_days": args.block_days, "near_ath_fraction": args.near_ath,
        "seed": args.seed, "results": results,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "results.json").write_text(json.dumps(metadata, indent=2) + "\n")
    with (args.output / "summary.csv").open("w", newline="") as handle:
        fields = ["horizon", "trading_days", "generated_paths", "retained_paths",
                  "retention_rate", "touch_rate", "finish_near_rate",
                  "soxx_terminal_retained_median", "soxl_probability_profit",
                  "soxl_probability_loss_25pct", "soxl_probability_gain_50pct",
                  "soxl_p05", "soxl_p25", "soxl_p50", "soxl_p75", "soxl_p95"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for result in results:
            row = {k: result[k] for k in fields if k in result}
            row.update({f"soxl_{q}": result["soxl_terminal"][q] for q in ["p05", "p25", "p50", "p75", "p95"]})
            writer.writerow(row)
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
