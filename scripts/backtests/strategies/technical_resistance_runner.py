#!/usr/bin/env python3
"""Execute the Technical Resistance Runner TC-001 portfolio backtest."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
ANALYSIS_DIR = ROOT / "scripts" / "analysis"
sys.path.insert(0, str(ANALYSIS_DIR))
import historical_setup_evaluator_snapshot as snapshot


EVALUATION_START = "2015-01-02"
EVALUATION_END = "2026-07-17"
DEVELOPMENT_END = "2024-12-31"
HOLDOUT_START = "2025-01-02"
MAX_HOLDING_DAYS = 126
FIRST_PROFIT_RETURN = 0.0521
FIRST_PROFIT_SALE_FRACTION = 0.75
INITIAL_CASH = 5000.0
EXIT_VARIANTS = (
    "full_at_5_21",
    "full_at_5_21_sma50_exit",
    "sequential_evaluator",
    "sequential_horizon",
)


def sma50_below_exit_signal(close, sma50):
    """Return whether a completed daily close invalidates the active position."""
    return close is not None and sma50 is not None and close < sma50


def sma50_next_open_exit_due(signal_date, current_date):
    """Return whether a prior after-close SMA50 signal is executable now."""
    return signal_date is not None and current_date > signal_date


def evaluate_sma50_exit(mode, close, sma50, state):
    """Evaluate one completed row and return ``(signal, updated_state)``."""
    updated = dict(state)
    if close is None or sma50 is None:
        return False, updated
    previous_close = updated.get("previous_close")
    previous_sma50 = updated.get("previous_sma50")
    below = close < sma50
    updated["armed"] = bool(updated.get("armed")) or close >= sma50
    updated["below_count"] = updated.get("below_count", 0) + 1 if below else 0
    if mode == "below":
        signal = below
    elif mode == "cross":
        signal = (
            previous_close is not None
            and previous_sma50 is not None
            and previous_close >= previous_sma50
            and below
        )
    elif mode == "confirmed_2":
        signal = updated["below_count"] >= 2
    elif mode == "armed_confirmed_2":
        signal = updated["armed"] and updated["below_count"] >= 2
    elif mode == "buffer_1pct":
        signal = close < sma50 * 0.99
    else:
        signal = False
    updated["previous_close"] = close
    updated["previous_sma50"] = sma50
    return signal, updated


def fixed_stop_fill_price(open_price, low, stop_price):
    """Return conservative stop fill price, or ``None`` when untouched."""
    if open_price is None or low is None or stop_price is None or low > stop_price:
        return None
    return min(open_price, stop_price)


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--universe",
        type=Path,
        default=ROOT / "configuration/universes/random-sp500-50-1.md",
    )
    parser.add_argument(
        "--features",
        type=Path,
        default=ROOT / "data/stock/features/daily",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "artifacts/stock/backtests/strategies/technical-resistance-runner/tc-001",
    )
    parser.add_argument("--exit-variant", choices=EXIT_VARIANTS, default="sequential_evaluator")
    parser.add_argument("--slippage-bps", type=float, default=0.0)
    parser.add_argument("--fee-per-order", type=float, default=0.0)
    parser.add_argument("--minimum-score", type=float)
    parser.add_argument("--maximum-support-distance-pct", type=float)
    parser.add_argument("--evaluation-start", default=EVALUATION_START)
    parser.add_argument("--evaluation-end", default=EVALUATION_END)
    parser.add_argument(
        "--sma50-exit-mode",
        choices=("below", "cross", "confirmed_2", "armed_confirmed_2", "buffer_1pct"),
    )
    parser.add_argument(
        "--stop-loss-return",
        type=float,
        help="Positive entry-relative full-position stop distance; disabled by default.",
    )
    parser.add_argument(
        "--market-regime-sma-window",
        type=int,
        choices=(150, 200),
        help="Enter only when SPY decision close is at or above this SMA.",
    )
    return parser.parse_args(argv)


def load_universe(path):
    tickers = []
    for line in path.read_text().splitlines():
        if line.startswith("- `") and line.endswith("`"):
            tickers.append(line[3:-1])
    if len(tickers) != 50 or len(set(tickers)) != 50:
        raise ValueError("universe must contain 50 unique tickers")
    return tickers


def rows_by_date(rows):
    return {row["date"]: row for row in rows}


def monthly_entry_dates(spy_rows, evaluation_start, evaluation_end):
    dates = [
        row["date"]
        for row in spy_rows
        if evaluation_start <= row["date"] <= evaluation_end
    ]
    first_by_month = {}
    for date in dates:
        first_by_month.setdefault(date[:7], date)
    all_dates = [row["date"] for row in spy_rows]
    result = {}
    for entry_date in first_by_month.values():
        index = all_dates.index(entry_date)
        if index == 0:
            continue
        result[entry_date] = all_dates[index - 1]
    return result


def select_winner(
    tickers,
    histories,
    spy_history,
    decision_date,
    minimum_score=None,
    maximum_support_distance_pct=None,
):
    spy_rows = snapshot.trailing(spy_history, decision_date)
    if len(spy_rows) < 253:
        return None
    spy_row = spy_rows[-1]
    candidates = {}
    relative_126 = {}
    exclusions = {}
    for ticker in tickers:
        rows = snapshot.trailing(histories[ticker], decision_date)
        if len(rows) < 253:
            exclusions[ticker] = "insufficient_history"
            continue
        required = ("adj_close", "adj_high", "adj_low", "volume", "sma_20", "sma_50", "sma_150", "ret_63", "ret_126", "ret_252")
        if any(snapshot.as_float(rows[-1].get(field)) is None for field in required):
            exclusions[ticker] = "missing_required_feature"
            continue
        support = snapshot.nearby_support(rows[-1], rows)
        price = snapshot.as_float(rows[-1]["adj_close"])
        resistance = max(snapshot.as_float(row["adj_high"]) for row in rows[-126:] if row.get("adj_high"))
        if support is None or resistance <= price or price <= support:
            exclusions[ticker] = "invalid_support_or_resistance"
            continue
        candidates[ticker] = (rows, support, resistance)
        relative_126[ticker] = (
            snapshot.as_float(rows[-1]["ret_126"])
            - snapshot.as_float(spy_row["ret_126"])
        )
    if not candidates:
        return None
    values = list(relative_126.values())
    scored = []
    for ticker, (rows, support, resistance) in candidates.items():
        score, details = snapshot.quantitative_score(
            rows,
            spy_row,
            snapshot.percentile(values, relative_126[ticker]),
        )
        scored.append({
            "ticker": ticker,
            "score": score,
            "support": support,
            "target": resistance,
            "decision_price": snapshot.as_float(rows[-1]["adj_close"]),
            "components": details,
        })
    scored.sort(key=lambda row: (-row["score"], row["ticker"]))
    if maximum_support_distance_pct is not None:
        scored = [
            row
            for row in scored
            if (row["decision_price"] / row["support"] - 1.0) * 100.0
            <= maximum_support_distance_pct
        ]
        if not scored:
            return None
    if minimum_score is not None and scored[0]["score"] < minimum_score:
        return None
    return scored[0], scored, exclusions


def max_drawdown(values):
    peak = None
    worst = 0.0
    for value in values:
        peak = value if peak is None else max(peak, value)
        worst = min(worst, value / peak - 1.0)
    return worst


def period_summary(label, equity_rows, trades, start, end):
    rows = [row for row in equity_rows if start <= row["date"] <= end]
    if not rows:
        return {}
    start_value = rows[0]["equity"]
    end_value = rows[-1]["equity"]
    years = max((len(rows) - 1) / 252.0, 1.0 / 252.0)
    period_trades = [row for row in trades if start <= row["entry_date"] <= end]
    returns = [row["return_pct"] for row in period_trades]
    return {
        "partition": label,
        "start": rows[0]["date"],
        "end": rows[-1]["date"],
        "start_equity": start_value,
        "end_equity": end_value,
        "total_return_pct": (end_value / start_value - 1.0) * 100.0,
        "cagr_pct": ((end_value / start_value) ** (1.0 / years) - 1.0) * 100.0,
        "max_drawdown_pct": max_drawdown([row["equity"] for row in rows]) * 100.0,
        "completed_trades": len(period_trades),
        "mean_trade_return_pct": statistics.mean(returns) if returns else None,
        "median_trade_return_pct": statistics.median(returns) if returns else None,
        "win_rate": sum(value > 0 for value in returns) / len(returns) if returns else None,
        "target_hit_rate": sum(row["first_target_date"] is not None for row in period_trades) / len(period_trades) if period_trades else None,
    }


def benchmark_return(history, start_date, end_date):
    rows = [row for row in history if start_date <= row["date"] <= end_date]
    if not rows:
        return None
    start = snapshot.as_float(rows[0]["adj_open"])
    end = snapshot.as_float(rows[-1]["adj_close"])
    if start is None or end is None:
        return None
    return (end / start - 1.0) * 100.0


def run(args):
    if args.slippage_bps < 0 or args.fee_per_order < 0:
        raise ValueError("slippage and fees must be non-negative")
    if args.stop_loss_return is not None and not 0 < args.stop_loss_return < 1:
        raise ValueError("stop-loss return must be between zero and one")
    args.universe = args.universe.resolve()
    args.features = args.features.resolve()
    args.output = args.output.resolve()
    slippage = args.slippage_bps / 10000.0
    sma50_exit_mode = args.sma50_exit_mode
    if args.exit_variant == "full_at_5_21_sma50_exit" and sma50_exit_mode is None:
        sma50_exit_mode = "below"
    tickers = load_universe(args.universe)
    histories = {ticker: snapshot.load_rows(args.features, ticker) for ticker in tickers}
    maps = {ticker: rows_by_date(rows) for ticker, rows in histories.items()}
    spy = snapshot.load_rows(args.features, "SPY")
    spy_map = rows_by_date(spy)
    calendar = [
        row["date"]
        for row in spy
        if args.evaluation_start <= row["date"] <= args.evaluation_end
    ]
    if not calendar:
        raise ValueError("evaluation window has no SPY sessions")
    global_index = {date: index for index, date in enumerate([row["date"] for row in spy])}
    entry_triggers = monthly_entry_dates(
        spy, args.evaluation_start, args.evaluation_end
    )

    cash = INITIAL_CASH
    position = None
    predictions = []
    trades = []
    equity_rows = []
    skipped_signals = 0

    for date in calendar:
        if date in entry_triggers:
            decision_date = entry_triggers[date]
            regime_allows_entry = True
            if args.market_regime_sma_window is not None:
                market_row = spy_map.get(decision_date)
                market_close = (
                    snapshot.as_float(market_row.get("adj_close"))
                    if market_row
                    else None
                )
                market_sma = (
                    snapshot.as_float(
                        market_row.get("sma_{}".format(args.market_regime_sma_window))
                    )
                    if market_row
                    else None
                )
                regime_allows_entry = (
                    market_close is not None
                    and market_sma is not None
                    and market_close >= market_sma
                )
            selected = (
                select_winner(
                    tickers,
                    histories,
                    spy,
                    decision_date,
                    args.minimum_score,
                    args.maximum_support_distance_pct,
                )
                if regime_allows_entry
                else None
            )
            if selected is not None:
                winner, ranked, exclusions = selected
                action = "skip_active_position" if position is not None else "enter"
                predictions.append({
                    "decision_date": decision_date,
                    "entry_date": date,
                    "ticker": winner["ticker"],
                    "score": winner["score"],
                    "decision_price": winner["decision_price"],
                    "support": winner["support"],
                    "target": winner["target"],
                    "action": action,
                    "eligible_count": len(ranked),
                    "excluded_count": len(exclusions),
                    "score_components": json.dumps(winner["components"], sort_keys=True),
                })
                if position is not None:
                    skipped_signals += 1
                else:
                    entry_row = maps[winner["ticker"]].get(date)
                    entry_price = snapshot.as_float(entry_row.get("adj_open")) if entry_row else None
                    if entry_price is not None and entry_price > 0:
                        fill_price = entry_price * (1.0 + slippage)
                        quantity = max(cash - args.fee_per_order, 0.0) / fill_price
                        position = {
                            "ticker": winner["ticker"],
                            "entry_date": date,
                            "entry_index": global_index[date],
                            "entry_price": fill_price,
                            "original_quantity": quantity,
                            "remaining_quantity": quantity,
                            "resistance_target": winner["target"],
                            "first_target": fill_price * (1.0 + FIRST_PROFIT_RETURN),
                            "stop_price": (
                                fill_price * (1.0 - args.stop_loss_return)
                                if args.stop_loss_return is not None
                                else None
                            ),
                            "second_target": max(winner["target"], fill_price * (1.0 + FIRST_PROFIT_RETURN)),
                            "first_target_date": None,
                            "second_target_date": None,
                            "sma50_exit_signal_date": None,
                            "sma50_state": {
                                "previous_close": None,
                                "previous_sma50": None,
                                "below_count": 0,
                                "armed": False,
                            },
                            "score": winner["score"],
                            "starting_capital": cash,
                        }
                        cash = 0.0

        if position is not None:
            ticker_row = maps[position["ticker"]].get(date)
            sessions_after_entry = global_index[date] - position["entry_index"]
            if (
                ticker_row
                and sma50_next_open_exit_due(position["sma50_exit_signal_date"], date)
            ):
                exit_price = snapshot.as_float(ticker_row["adj_open"])
                proceeds = (
                    position["remaining_quantity"] * exit_price * (1.0 - slippage)
                    - args.fee_per_order
                )
                cash += proceeds
                total_return = cash / position["starting_capital"] - 1.0
                trades.append({
                    "ticker": position["ticker"],
                    "entry_date": position["entry_date"],
                    "entry_price": position["entry_price"],
                    "score": position["score"],
                    "first_target": position["first_target"],
                    "first_target_date": position["first_target_date"],
                    "resistance_target": position["resistance_target"],
                    "second_target": position["second_target"],
                    "second_target_date": position["second_target_date"],
                    "exit_date": date,
                    "exit_reason": "sma50_next_open",
                    "exit_price": exit_price,
                    "holding_sessions": sessions_after_entry,
                    "starting_capital": position["starting_capital"],
                    "ending_capital": cash,
                    "return_pct": total_return * 100.0,
                })
                position = None
                ticker_row = None
            if (
                ticker_row
                and sessions_after_entry >= 1
                and position["stop_price"] is not None
            ):
                low = snapshot.as_float(ticker_row["adj_low"])
                open_price = snapshot.as_float(ticker_row["adj_open"])
                exit_price = fixed_stop_fill_price(
                    open_price, low, position["stop_price"]
                )
                if exit_price is not None:
                    proceeds = (
                        position["remaining_quantity"]
                        * exit_price
                        * (1.0 - slippage)
                        - args.fee_per_order
                    )
                    cash += proceeds
                    total_return = cash / position["starting_capital"] - 1.0
                    trades.append({
                        "ticker": position["ticker"],
                        "entry_date": position["entry_date"],
                        "entry_price": position["entry_price"],
                        "score": position["score"],
                        "first_target": position["first_target"],
                        "first_target_date": position["first_target_date"],
                        "resistance_target": position["resistance_target"],
                        "second_target": position["second_target"],
                        "second_target_date": position["second_target_date"],
                        "exit_date": date,
                        "exit_reason": "fixed_stop",
                        "exit_price": exit_price,
                        "holding_sessions": sessions_after_entry,
                        "starting_capital": position["starting_capital"],
                        "ending_capital": cash,
                        "return_pct": total_return * 100.0,
                    })
                    position = None
                    ticker_row = None
            if ticker_row and sessions_after_entry >= 1:
                high = snapshot.as_float(ticker_row["adj_high"])
                if position["first_target_date"] is None and high is not None and high >= position["first_target"]:
                    sale_fraction = (
                        1.0
                        if args.exit_variant in ("full_at_5_21", "full_at_5_21_sma50_exit")
                        else FIRST_PROFIT_SALE_FRACTION
                    )
                    quantity = position["original_quantity"] * sale_fraction
                    proceeds = (
                        quantity * position["first_target"] * (1.0 - slippage)
                        - args.fee_per_order
                    )
                    position["remaining_quantity"] -= quantity
                    position["first_target_date"] = date
                    cash += proceeds
                if (
                    args.exit_variant == "sequential_evaluator"
                    and
                    position["first_target_date"] is not None
                    and position["second_target_date"] is None
                    and high is not None
                    and high >= position["second_target"]
                ):
                    proceeds = (
                        position["remaining_quantity"] * position["second_target"] * (1.0 - slippage)
                        - args.fee_per_order
                    )
                    cash += proceeds
                    position["remaining_quantity"] = 0.0
                    position["second_target_date"] = date
                if position["remaining_quantity"] <= 1e-12:
                    total_return = cash / position["starting_capital"] - 1.0
                    trades.append({
                        "ticker": position["ticker"],
                        "entry_date": position["entry_date"],
                        "entry_price": position["entry_price"],
                        "score": position["score"],
                        "first_target": position["first_target"],
                        "first_target_date": position["first_target_date"],
                        "resistance_target": position["resistance_target"],
                        "second_target": position["second_target"],
                        "second_target_date": position["second_target_date"],
                        "exit_date": date,
                        "exit_reason": (
                            "first_target"
                            if args.exit_variant in ("full_at_5_21", "full_at_5_21_sma50_exit")
                            else "second_target"
                        ),
                        "exit_price": (
                            position["first_target"]
                            if args.exit_variant in ("full_at_5_21", "full_at_5_21_sma50_exit")
                            else position["second_target"]
                        ),
                        "holding_sessions": sessions_after_entry,
                        "starting_capital": position["starting_capital"],
                        "ending_capital": cash,
                        "return_pct": total_return * 100.0,
                    })
                    position = None
                elif sessions_after_entry >= MAX_HOLDING_DAYS:
                    exit_price = snapshot.as_float(ticker_row["adj_close"])
                    proceeds = (
                        position["remaining_quantity"] * exit_price * (1.0 - slippage)
                        - args.fee_per_order
                    )
                    cash += proceeds
                    total_return = cash / position["starting_capital"] - 1.0
                    trades.append({
                        "ticker": position["ticker"],
                        "entry_date": position["entry_date"],
                        "entry_price": position["entry_price"],
                        "score": position["score"],
                        "first_target": position["first_target"],
                        "first_target_date": position["first_target_date"],
                        "resistance_target": position["resistance_target"],
                        "second_target": position["second_target"],
                        "second_target_date": position["second_target_date"],
                        "exit_date": date,
                        "exit_reason": "horizon",
                        "exit_price": exit_price,
                        "holding_sessions": sessions_after_entry,
                        "starting_capital": position["starting_capital"],
                        "ending_capital": cash,
                        "return_pct": total_return * 100.0,
                    })
                    position = None
                elif sma50_exit_mode is not None:
                    close = snapshot.as_float(ticker_row["adj_close"])
                    sma50 = snapshot.as_float(ticker_row["sma_50"])
                    signal, position["sma50_state"] = evaluate_sma50_exit(
                        sma50_exit_mode, close, sma50, position["sma50_state"]
                    )
                    if signal:
                        position["sma50_exit_signal_date"] = date
            if (
                position is not None
                and ticker_row
                and sessions_after_entry == 0
                and sma50_exit_mode is not None
            ):
                close = snapshot.as_float(ticker_row["adj_close"])
                sma50 = snapshot.as_float(ticker_row["sma_50"])
                signal, position["sma50_state"] = evaluate_sma50_exit(
                    sma50_exit_mode, close, sma50, position["sma50_state"]
                )
                if signal:
                    position["sma50_exit_signal_date"] = date

        equity = cash
        active_ticker = ""
        if position is not None:
            active_ticker = position["ticker"]
            row = maps[active_ticker].get(date)
            if row:
                equity += position["remaining_quantity"] * snapshot.as_float(row["adj_close"])
        equity_rows.append({"date": date, "equity": equity, "cash": cash, "ticker": active_ticker})

    first_date = equity_rows[0]["date"]
    last_date = equity_rows[-1]["date"]
    spy_return = benchmark_return(spy, first_date, last_date)
    equal_weight_returns = [
        value
        for value in (
            benchmark_return(histories[ticker], first_date, last_date)
            for ticker in tickers
        )
        if value is not None
    ]
    equal_weight_return = statistics.mean(equal_weight_returns)
    summaries = [
        period_summary(
            "full", equity_rows, trades, args.evaluation_start, args.evaluation_end
        )
    ]
    if (
        args.evaluation_start == EVALUATION_START
        and args.evaluation_end == EVALUATION_END
    ):
        summaries.extend(
            [
                period_summary(
                    "development",
                    equity_rows,
                    trades,
                    EVALUATION_START,
                    DEVELOPMENT_END,
                ),
                period_summary(
                    "retrospective_2025_2026",
                    equity_rows,
                    trades,
                    HOLDOUT_START,
                    EVALUATION_END,
                ),
            ]
        )
    full = summaries[0]
    full.update({
        "spy_return_pct": spy_return,
        "equal_weight_universe_return_pct": equal_weight_return,
        "excess_vs_spy_pct": full["total_return_pct"] - spy_return,
        "excess_vs_equal_weight_pct": full["total_return_pct"] - equal_weight_return,
        "monthly_predictions": len(predictions),
        "skipped_active_signals": skipped_signals,
        "open_position_at_end": position["ticker"] if position else None,
    })

    args.output.mkdir(parents=True, exist_ok=True)
    write_csv(args.output / "predictions.csv", predictions)
    write_csv(args.output / "trades.csv", trades)
    write_csv(args.output / "equity_curve.csv", equity_rows)
    write_csv(args.output / "summary.csv", summaries)
    payload = {
        "config": {
            "universe": str(args.universe.relative_to(ROOT)),
            "evaluation_start": args.evaluation_start,
            "evaluation_end": args.evaluation_end,
            "equal_weight_constituents_with_history": len(equal_weight_returns),
            "first_profit_return": FIRST_PROFIT_RETURN,
            "first_profit_sale_fraction": FIRST_PROFIT_SALE_FRACTION,
            "second_profit_sale_fraction": 1.0 - FIRST_PROFIT_SALE_FRACTION,
            "exit_variant": args.exit_variant,
            "slippage_bps": args.slippage_bps,
            "fee_per_order": args.fee_per_order,
            "minimum_score": args.minimum_score,
            "maximum_support_distance_pct": args.maximum_support_distance_pct,
            "sma50_exit_mode": sma50_exit_mode,
            "stop_loss_return": args.stop_loss_return,
            "market_regime_sma_window": args.market_regime_sma_window,
            "maximum_holding_days": MAX_HOLDING_DAYS,
            "initial_cash": INITIAL_CASH,
            "entry_fill": "next_session_adjusted_open",
            "target_fill": "first_later_adjusted_high_touch_at_limit",
            "horizon_fill": "adjusted_close",
        },
        "summary": summaries,
        "open_position": position,
    }
    (args.output / "results.json").write_text(json.dumps(payload, indent=2) + "\n")
    (args.output / "execution-report.md").write_text(render_report(summaries, predictions, trades, position))
    return payload


def write_csv(path, rows):
    if not rows:
        path.write_text("")
        return
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def fmt(value):
    return "N/A" if value is None else "{:.2f}".format(value)


def render_report(summaries, predictions, trades, position):
    lines = [
        "# Technical Resistance Runner TC-001 Execution Report",
        "",
        "| Partition | Total Return | CAGR | Max Drawdown | Trades | Mean Trade | Win Rate | Target Hit Rate |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summaries:
        lines.append(
            "| {partition} | {total}% | {cagr}% | {drawdown}% | {trades} | {mean}% | {win}% | {hit}% |".format(
                partition=row["partition"],
                total=fmt(row.get("total_return_pct")),
                cagr=fmt(row.get("cagr_pct")),
                drawdown=fmt(row.get("max_drawdown_pct")),
                trades=row.get("completed_trades", 0),
                mean=fmt(row.get("mean_trade_return_pct")),
                win=fmt(row.get("win_rate") * 100.0 if row.get("win_rate") is not None else None),
                hit=fmt(row.get("target_hit_rate") * 100.0 if row.get("target_hit_rate") is not None else None),
            )
        )
    full = summaries[0]
    lines += [
        "",
        "## Full-Period Benchmarks",
        "",
        "- SPY: {}%".format(fmt(full.get("spy_return_pct"))),
        "- Equal-weight universe 1: {}%".format(fmt(full.get("equal_weight_universe_return_pct"))),
        "- Strategy excess versus SPY: {} percentage points".format(fmt(full.get("excess_vs_spy_pct"))),
        "- Strategy excess versus equal weight: {} percentage points".format(fmt(full.get("excess_vs_equal_weight_pct"))),
        "",
        "## Operations",
        "",
        "- Monthly predictions: {}".format(len(predictions)),
        "- Completed trades: {}".format(len(trades)),
        "- Skipped signals while active: {}".format(full.get("skipped_active_signals")),
        "- Open position at evaluation end: {}".format(position["ticker"] if position else "None"),
        "",
        "This is a current-constituent-biased research test with frictionless adjusted-bar fills.",
    ]
    return "\n".join(lines) + "\n"


def main(argv=None):
    args = parse_args(argv)
    payload = run(args)
    print(json.dumps(payload["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
