#!/usr/bin/env python3
"""Run 25 point-in-time quantitative-swing ranking and target-exit scenarios."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import random
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import historical_setup_evaluator_snapshot as snapshot


TRADING_MONTH = 21
MAX_HORIZON = 126
BOOTSTRAP_LOOKBACK = 252
BOOTSTRAP_BLOCK = 5


def normalize_dates(seed, spy_rows, count=5):
    available = [row["date"] for row in spy_rows]
    start = dt.date(2015, 1, 1)
    end = dt.date(2025, 1, 31)
    rng = random.Random(seed)
    normalized = set()
    while len(normalized) < count:
        candidate = start + dt.timedelta(days=rng.randrange((end - start).days + 1))
        eligible = [date for date in available if date <= candidate.isoformat()]
        normalized.add(eligible[-1])
    return sorted(normalized)


def decision_index(rows, date):
    eligible = [index for index, row in enumerate(rows) if row["date"] <= date]
    return eligible[-1] if eligible else None


def target_for(rows):
    highs = [snapshot.as_float(row.get("adj_high")) for row in rows[-126:]]
    return max(value for value in highs if value is not None)


def atr14(rows):
    selected = rows[-15:]
    true_ranges = []
    for previous, current in zip(selected, selected[1:]):
        high = snapshot.as_float(current.get("adj_high"))
        low = snapshot.as_float(current.get("adj_low"))
        previous_close = snapshot.as_float(previous.get("adj_close"))
        if high is not None and low is not None and previous_close is not None:
            true_ranges.append(max(high - low, abs(high - previous_close), abs(low - previous_close)))
    return sum(true_ranges) / len(true_ranges) if len(true_ranges) == 14 else None


def support_minus_two_atr_stop(rows):
    support = snapshot.nearby_support(rows[-1], rows)
    atr = atr14(rows)
    if support is None or atr is None:
        return None, support, atr
    return support - 2.0 * atr, support, atr


def horizon_forecast(rows, target, paths, seed):
    closes = np.array([snapshot.as_float(row["adj_close"]) for row in rows[-(BOOTSTRAP_LOOKBACK + 1):]])
    returns = closes[1:] / closes[:-1] - 1.0
    if len(returns) < BOOTSTRAP_LOOKBACK:
        raise ValueError("insufficient bootstrap history")
    starts = np.arange(len(returns) - BOOTSTRAP_BLOCK + 1)
    blocks = (MAX_HORIZON + BOOTSTRAP_BLOCK - 1) // BOOTSTRAP_BLOCK
    rng = np.random.default_rng(seed)
    chosen = rng.choice(starts, size=(paths, blocks), replace=True)
    offsets = np.arange(BOOTSTRAP_BLOCK)
    sampled = returns[chosen[..., None] + offsets].reshape(paths, blocks * BOOTSTRAP_BLOCK)[:, :MAX_HORIZON]
    simulated = closes[-1] * np.cumprod(1.0 + sampled, axis=1)
    hits = simulated >= target
    any_hit = hits.any(axis=1)
    first_hit = np.where(any_hit, hits.argmax(axis=1) + 1, 0)
    bucket_probabilities = {}
    cumulative_probabilities = {}
    for month in range(1, 7):
        lower = (month - 1) * TRADING_MONTH + 1
        upper = month * TRADING_MONTH
        bucket_probabilities["{}m".format(month)] = float(np.mean((first_hit >= lower) & (first_hit <= upper)))
        cumulative_probabilities["{}m".format(month)] = float(np.mean(any_hit & (first_hit <= upper)))
    modal = max(bucket_probabilities, key=lambda label: (bucket_probabilities[label], -int(label[:-1])))
    return {
        "modal_first_hit_horizon": modal,
        "modal_first_hit_probability": bucket_probabilities[modal],
        "first_hit_bucket_probabilities": bucket_probabilities,
        "cumulative_target_hit_probabilities": cumulative_probabilities,
        "no_hit_probability_6m": float(np.mean(~any_hit)),
    }


def actual_outcome(all_rows, index, target):
    future = all_rows[index + 1:index + 1 + MAX_HORIZON]
    if len(future) < MAX_HORIZON:
        raise ValueError("insufficient outcome history")
    entry = snapshot.as_float(all_rows[index]["adj_close"])
    for offset, row in enumerate(future, start=1):
        high = snapshot.as_float(row.get("adj_high"))
        if high is not None and high >= target:
            return {
                "exit_reason": "take_profit",
                "exit_date": row["date"],
                "exit_trading_day": offset,
                "exit_price": target,
                "return_pct": (target / entry - 1.0) * 100.0,
            }
    exit_row = future[-1]
    exit_price = snapshot.as_float(exit_row["adj_close"])
    return {
        "exit_reason": "six_month_market",
        "exit_date": exit_row["date"],
        "exit_trading_day": MAX_HORIZON,
        "exit_price": exit_price,
        "return_pct": (exit_price / entry - 1.0) * 100.0,
    }


def half_take_profit_with_stop_outcome(all_rows, index, target, stop_price):
    future = all_rows[index + 1:index + 1 + MAX_HORIZON]
    if len(future) < MAX_HORIZON:
        raise ValueError("insufficient outcome history")
    entry = snapshot.as_float(all_rows[index]["adj_close"])
    stop = stop_price
    stop_loss = stop / entry - 1.0
    target_return = target / entry - 1.0
    target_date = None
    target_day = None
    for offset, row in enumerate(future, start=1):
        low = snapshot.as_float(row.get("adj_low"))
        high = snapshot.as_float(row.get("adj_high"))
        # Daily bars do not reveal event order. Use the conservative stop-first
        # assumption whenever both levels lie inside the same bar.
        if low is not None and low <= stop:
            if target_date is None:
                return {
                    "partial_exit_reason": "full_stop_before_target",
                    "partial_exit_date": row["date"],
                    "partial_target_date": None,
                    "partial_stop_price": stop,
                    "partial_return_pct": stop_loss * 100.0,
                }
            blended = 0.5 * target_return + 0.5 * stop_loss
            return {
                "partial_exit_reason": "half_target_half_stop",
                "partial_exit_date": row["date"],
                "partial_target_date": target_date,
                "partial_stop_price": stop,
                "partial_return_pct": blended * 100.0,
            }
        if target_date is None and high is not None and high >= target:
            target_date = row["date"]
            target_day = offset

    horizon_close = snapshot.as_float(future[-1]["adj_close"])
    horizon_return = horizon_close / entry - 1.0
    if target_date is not None:
        blended = 0.5 * target_return + 0.5 * horizon_return
        return {
            "partial_exit_reason": "half_target_half_six_month_market",
            "partial_exit_date": future[-1]["date"],
            "partial_target_date": target_date,
            "partial_stop_price": stop,
            "partial_return_pct": blended * 100.0,
        }
    return {
        "partial_exit_reason": "full_six_month_market",
        "partial_exit_date": future[-1]["date"],
        "partial_target_date": None,
        "partial_stop_price": stop,
        "partial_return_pct": horizon_return * 100.0,
    }


def no_stop_half_take_profit_outcome(all_rows, index, target):
    future = all_rows[index + 1:index + 1 + MAX_HORIZON]
    if len(future) < MAX_HORIZON:
        raise ValueError("insufficient outcome history")
    entry = snapshot.as_float(all_rows[index]["adj_close"])
    horizon_close = snapshot.as_float(future[-1]["adj_close"])
    horizon_return = horizon_close / entry - 1.0
    for offset, row in enumerate(future, start=1):
        high = snapshot.as_float(row.get("adj_high"))
        if high is not None and high >= target:
            target_return = target / entry - 1.0
            return {
                "no_stop_half_exit_reason": "half_target_half_six_month_market",
                "no_stop_half_target_date": row["date"],
                "no_stop_half_target_day": offset,
                "no_stop_half_return_pct": 0.5 * (target_return + horizon_return) * 100.0,
            }
    return {
        "no_stop_half_exit_reason": "full_six_month_market",
        "no_stop_half_target_date": None,
        "no_stop_half_target_day": None,
        "no_stop_half_return_pct": horizon_return * 100.0,
    }


def half_target_half_stop_scale_out_outcome(all_rows, index, target, stop_loss_pct=0.10):
    future = all_rows[index + 1:index + 1 + MAX_HORIZON]
    if len(future) < MAX_HORIZON:
        raise ValueError("insufficient outcome history")
    entry = snapshot.as_float(all_rows[index]["adj_close"])
    target_return = target / entry - 1.0
    stop = entry * (1.0 - stop_loss_pct)
    realized_return = 0.0
    remaining_weight = 1.0
    target_date = None
    stop_date = None
    for row in future:
        low = snapshot.as_float(row.get("adj_low"))
        high = snapshot.as_float(row.get("adj_high"))
        # Each level controls one half of the original position. If both levels
        # lie inside the same daily bar, both half-orders are treated as filled.
        if stop_date is None and low is not None and low <= stop:
            stop_date = row["date"]
            realized_return += 0.5 * (-stop_loss_pct)
            remaining_weight -= 0.5
        if target_date is None and high is not None and high >= target:
            target_date = row["date"]
            realized_return += 0.5 * target_return
            remaining_weight -= 0.5
        if remaining_weight <= 0:
            break
    horizon_close = snapshot.as_float(future[-1]["adj_close"])
    if remaining_weight > 0:
        realized_return += remaining_weight * (horizon_close / entry - 1.0)
    if target_date and stop_date:
        reason = "half_target_half_stop"
    elif target_date:
        reason = "half_target_half_six_month_market"
    elif stop_date:
        reason = "half_stop_half_six_month_market"
    else:
        reason = "full_six_month_market"
    return {
        "scale_out_exit_reason": reason,
        "scale_out_target_date": target_date,
        "scale_out_stop_date": stop_date,
        "scale_out_stop_price": stop,
        "scale_out_return_pct": realized_return * 100.0,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--constituents", type=Path, required=True)
    parser.add_argument("--features", type=Path, default=Path("data/stock/features/daily"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260723)
    parser.add_argument("--bootstrap-paths", type=int, default=20000)
    parser.add_argument("--scale-out-stop-loss-pct", type=float, default=0.15)
    args = parser.parse_args()

    with args.constituents.open(newline="") as handle:
        constituents = sorted({row["Symbol"].replace(".", "-") for row in csv.DictReader(handle)})
    available = {path.stem for path in (args.features / "2025").glob("*.csv")}
    spy_rows = snapshot.load_rows(args.features, "SPY")
    dates = normalize_dates(args.seed + 1, spy_rows)

    rows_by_ticker = {}
    eligible = []
    for ticker in sorted(set(constituents) & available):
        rows = snapshot.load_rows(args.features, ticker)
        valid = True
        for date in dates:
            index = decision_index(rows, date)
            if index is None or index < BOOTSTRAP_LOOKBACK or len(rows) - index - 1 < MAX_HORIZON:
                valid = False
                break
        if valid:
            rows_by_ticker[ticker] = rows
            eligible.append(ticker)
    if len(eligible) < 250:
        raise ValueError("need 250 eligible stocks, found {}".format(len(eligible)))

    shuffled = eligible[:]
    random.Random(args.seed).shuffle(shuffled)
    batches = [sorted(shuffled[index * 50:(index + 1) * 50]) for index in range(5)]
    scenarios = []
    for batch_index, batch in enumerate(batches, start=1):
        for date_index, date in enumerate(dates, start=1):
            spy_decision = snapshot.trailing(spy_rows, date)[-1]
            relative_126 = {}
            decision_rows = {}
            for ticker in batch:
                ticker_rows = snapshot.trailing(rows_by_ticker[ticker], date)
                decision_rows[ticker] = ticker_rows
                relative_126[ticker] = (
                    snapshot.as_float(ticker_rows[-1].get("ret_126"))
                    - snapshot.as_float(spy_decision.get("ret_126"))
                )
            rs_values = list(relative_126.values())
            scored = []
            for ticker in batch:
                score, details = snapshot.quantitative_score(
                    decision_rows[ticker],
                    spy_decision,
                    snapshot.percentile(rs_values, relative_126[ticker]),
                )
                scored.append((score, ticker, details))
            score, winner, details = max(scored, key=lambda item: (item[0], item[1]))
            rows = rows_by_ticker[winner]
            index = decision_index(rows, date)
            asof_rows = rows[:index + 1]
            entry = snapshot.as_float(asof_rows[-1]["adj_close"])
            target = target_for(asof_rows)
            target_upside = (target / entry - 1.0) * 100.0
            scenario_number = (batch_index - 1) * 5 + date_index
            forecast = horizon_forecast(
                asof_rows,
                target,
                args.bootstrap_paths,
                args.seed + scenario_number * 1009,
            )
            outcome = actual_outcome(rows, index, target)
            stop, support, atr = support_minus_two_atr_stop(asof_rows)
            if stop is None:
                raise ValueError("unable to construct stop for {} on {}".format(winner, date))
            partial_outcome = half_take_profit_with_stop_outcome(
                rows, index, target, stop_price=stop
            )
            no_stop_half_outcome = no_stop_half_take_profit_outcome(rows, index, target)
            scale_out_outcome = half_target_half_stop_scale_out_outcome(
                rows, index, target, stop_loss_pct=args.scale_out_stop_loss_pct
            )
            scenarios.append({
                "scenario": scenario_number,
                "batch": batch_index,
                "date_number": date_index,
                "evaluation_date": asof_rows[-1]["date"],
                "winner": winner,
                "final_score": score,
                "score_components": details,
                "entry_price": entry,
                "take_profit": target,
                "take_profit_upside_pct": target_upside,
                "stop_support": support,
                "stop_atr14": atr,
                "stop_price": stop,
                "stop_downside_pct": (stop / entry - 1.0) * 100.0,
                **forecast,
                **outcome,
                **partial_outcome,
                **no_stop_half_outcome,
                **scale_out_outcome,
            })

    returns = [row["return_pct"] for row in scenarios]
    target_exits = [row for row in scenarios if row["exit_reason"] == "take_profit"]
    partial_returns = [row["partial_return_pct"] for row in scenarios]
    no_stop_half_returns = [row["no_stop_half_return_pct"] for row in scenarios]
    scale_out_returns = [row["scale_out_return_pct"] for row in scenarios]
    summary = {
        "seed": args.seed,
        "date_seed": args.seed + 1,
        "dates": dates,
        "eligible_count": len(eligible),
        "batches": batches,
        "batch_overlap_count": sum(len(set(batches[i]) & set(batches[j])) for i in range(5) for j in range(i + 1, 5)),
        "bootstrap_paths_per_scenario": args.bootstrap_paths,
        "partial_strategy_stop_model": "support - 2*ATR14",
        "partial_strategy_average_stop_downside_pct": float(np.mean([row["stop_downside_pct"] for row in scenarios])),
        "average_outcome_pct": float(np.mean(returns)),
        "median_outcome_pct": float(np.median(returns)),
        "positive_outcome_rate": float(np.mean(np.array(returns) > 0)),
        "take_profit_exit_rate": len(target_exits) / len(scenarios),
        "average_take_profit_days_when_hit": float(np.mean([row["exit_trading_day"] for row in target_exits])) if target_exits else None,
        "partial_strategy_average_outcome_pct": float(np.mean(partial_returns)),
        "partial_strategy_median_outcome_pct": float(np.median(partial_returns)),
        "partial_strategy_positive_outcome_rate": float(np.mean(np.array(partial_returns) > 0)),
        "partial_strategy_exit_reason_counts": {
            reason: sum(row["partial_exit_reason"] == reason for row in scenarios)
            for reason in sorted({row["partial_exit_reason"] for row in scenarios})
        },
        "no_stop_half_strategy_average_outcome_pct": float(np.mean(no_stop_half_returns)),
        "no_stop_half_strategy_median_outcome_pct": float(np.median(no_stop_half_returns)),
        "no_stop_half_strategy_positive_outcome_rate": float(np.mean(np.array(no_stop_half_returns) > 0)),
        "no_stop_half_strategy_exit_reason_counts": {
            reason: sum(row["no_stop_half_exit_reason"] == reason for row in scenarios)
            for reason in sorted({row["no_stop_half_exit_reason"] for row in scenarios})
        },
        "scale_out_strategy_stop_loss_pct": args.scale_out_stop_loss_pct,
        "scale_out_strategy_average_outcome_pct": float(np.mean(scale_out_returns)),
        "scale_out_strategy_median_outcome_pct": float(np.median(scale_out_returns)),
        "scale_out_strategy_positive_outcome_rate": float(np.mean(np.array(scale_out_returns) > 0)),
        "scale_out_strategy_exit_reason_counts": {
            reason: sum(row["scale_out_exit_reason"] == reason for row in scenarios)
            for reason in sorted({row["scale_out_exit_reason"] for row in scenarios})
        },
        "scenario_count": len(scenarios),
    }
    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / "results.json").open("w") as handle:
        json.dump({"summary": summary, "scenarios": scenarios}, handle, indent=2)
        handle.write("\n")
    with (args.output / "scenarios.csv").open("w", newline="") as handle:
        fields = [
            "scenario", "batch", "evaluation_date", "winner", "final_score",
            "entry_price", "take_profit", "take_profit_upside_pct",
            "stop_support", "stop_atr14", "stop_price", "stop_downside_pct",
            "modal_first_hit_horizon", "modal_first_hit_probability",
            "no_hit_probability_6m", "exit_reason", "exit_date",
            "exit_trading_day", "exit_price", "return_pct",
            "partial_stop_price", "partial_target_date", "partial_exit_reason",
            "partial_exit_date", "partial_return_pct",
            "no_stop_half_exit_reason", "no_stop_half_target_date",
            "no_stop_half_target_day", "no_stop_half_return_pct",
            "scale_out_exit_reason", "scale_out_target_date", "scale_out_stop_date",
            "scale_out_stop_price", "scale_out_return_pct",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(scenarios)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
