#!/usr/bin/env python3
"""Run the frozen classic 12-1 point-in-time S&P 500 rotation scenario."""

from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import json
import math
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
FEATURE_ROOT = ROOT / "data/stock/features/daily"
MEMBERSHIP_PATH = ROOT / "data/stock/universes/sp500-historical-membership.csv"
INTEGRITY_PATH = ROOT / "data/stock/prices/daily/.integrity.md"
OUTPUT_ROOT = ROOT / (
    "artifacts/stock/backtests/strategies/"
    "classic-12-1-momentum-rotation/tc-001"
)
GATED_OUTPUT_ROOT = ROOT / (
    "artifacts/stock/backtests/strategies/"
    "regime-gated-classic-12-1-momentum/tc-001"
)
DEFAULT_WARMUP_START = "2020-01-02"
DEFAULT_START = "2021-01-04"
DEFAULT_END = "2026-07-02"
INITIAL_CASH = 5000.0
TARGET_COUNT = 10


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--warmup-start", default=DEFAULT_WARMUP_START)
    parser.add_argument("--evaluation-start", default=DEFAULT_START)
    parser.add_argument("--evaluation-end", default=DEFAULT_END)
    parser.add_argument("--slippage-bps", type=float, default=0.0)
    parser.add_argument("--fee-per-order", type=float, default=0.0)
    parser.add_argument("--market-sma-window", type=int, choices=(200,))
    return parser.parse_args(argv)


def number(value):
    try:
        result = None if value in (None, "") else float(value)
    except (TypeError, ValueError):
        return None
    return result if result is not None and math.isfinite(result) else None


def normalize_ticker(ticker):
    return ticker.replace(".", "-")


def load_memberships():
    with MEMBERSHIP_PATH.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    dates = [row["date"] for row in rows]
    memberships = {
        row["date"]: [normalize_ticker(value) for value in row["tickers"].split(",")]
        for row in rows
    }
    return dates, memberships


def resolve_membership(cutoff, dates, memberships):
    position = bisect.bisect_right(dates, cutoff) - 1
    if position < 0:
        raise RuntimeError("no membership snapshot for {}".format(cutoff))
    date = dates[position]
    return date, memberships[date]


def load_gap_symbols():
    symbols = set()
    active = False
    for line in INTEGRITY_PATH.read_text(encoding="utf-8").splitlines():
        if line == "## Supported-Calendar Internal Gaps":
            active = True
            continue
        if active and line.startswith("## "):
            break
        if active and line.startswith("- `"):
            symbols.add(line.split("`", 2)[1])
    return symbols


def load_tape(ticker):
    rows = []
    for path in sorted(FEATURE_ROOT.glob("*/{}.csv".format(ticker))):
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                date = row.get("date", "")
                close = number(row.get("adj_close"))
                adjusted_open = number(row.get("adj_open"))
                if date and close is not None and adjusted_open is not None:
                    rows.append((
                        date, adjusted_open, close, number(row.get("sma_200"))
                    ))
    rows.sort()
    if not rows:
        return None
    return {
        "rows": rows,
        "dates": [row[0] for row in rows],
        "index": {row[0]: index for index, row in enumerate(rows)},
    }


def monthly_cutoffs(spy, start, end):
    last_by_month = {}
    for date in spy["dates"]:
        if start <= date <= end:
            last_by_month[date[:7]] = date
    return list(last_by_month.values())


def next_date(spy, date, offset=1):
    position = bisect.bisect_right(spy["dates"], date)
    target = position + offset - 1
    return spy["dates"][target] if target < len(spy["dates"]) else None


def price_on(tape, date, field):
    if tape is None:
        return None
    position = tape["index"].get(date)
    return None if position is None else tape["rows"][position][field]


def latest_close_on_or_before(tape, date):
    if tape is None:
        return None
    position = bisect.bisect_right(tape["dates"], date) - 1
    return None if position < 0 else tape["rows"][position][2]


def select_targets(cutoff, members, tapes, gap_symbols):
    scores = []
    exclusions = defaultdict(int)
    for ticker in sorted(set(members)):
        if ticker in gap_symbols:
            exclusions["internal_price_gaps"] += 1
            continue
        tape = tapes.get(ticker)
        if tape is None or cutoff not in tape["index"]:
            exclusions["missing_cutoff_price"] += 1
            continue
        index = tape["index"][cutoff]
        if index < 252:
            exclusions["insufficient_history"] += 1
            continue
        start = tape["rows"][index - 252][2]
        skipped = tape["rows"][index - 21][2]
        if start is None or skipped is None or start <= 0:
            exclusions["invalid_signal_price"] += 1
            continue
        scores.append((skipped / start - 1.0, ticker))
    scores.sort(key=lambda item: (-item[0], item[1]))
    selected = [ticker for _, ticker in scores[:TARGET_COUNT]]
    return selected, scores, dict(exclusions)


def marked_value(cash, positions, tapes, date):
    total = cash
    missing = []
    for ticker, shares in positions.items():
        close = latest_close_on_or_before(tapes.get(ticker), date)
        if close is None:
            missing.append(ticker)
        else:
            total += shares * close
    if missing:
        raise RuntimeError(
            "cannot value positions on {}: {}".format(date, ",".join(sorted(missing)))
        )
    return total


def execute_sale_stage(
    signal_date,
    sell_date,
    settlement_date,
    selected,
    cash,
    positions,
    tapes,
    slippage_bps,
    fee_per_order,
    trades,
):
    target_weight = 1.0 / len(selected) if selected else 0.0
    selected_set = set(selected)
    pretrade_value = marked_value(cash, positions, tapes, signal_date)
    sale_proceeds = 0.0

    # The first execution session sells removals and trims continuing positions.
    for ticker in sorted(list(positions)):
        raw = price_on(tapes.get(ticker), sell_date, 1)
        if raw is None:
            continue
        sell_price = raw * (1.0 - slippage_bps / 10000.0)
        target_value = pretrade_value * target_weight if ticker in selected_set else 0.0
        current_value = positions[ticker] * raw
        sell_value = max(0.0, current_value - target_value)
        shares = min(positions[ticker], sell_value / raw)
        if shares <= 1e-12:
            continue
        gross = shares * sell_price
        net = max(0.0, gross - fee_per_order)
        positions[ticker] -= shares
        if positions[ticker] <= 1e-12:
            del positions[ticker]
        sale_proceeds += net
        trades.append({
            "signal_date": signal_date, "trade_date": sell_date,
            "ticker": ticker, "side": "SELL", "shares": shares,
            "price": sell_price, "gross_value": gross,
            "fee": fee_per_order, "settlement_date": settlement_date,
        })

    # Only cash already settled before the cycle may be spent on the sale date.
    cash = buy_shortfalls(
        signal_date, sell_date, selected, cash, pretrade_value, target_weight,
        positions, tapes, slippage_bps, fee_per_order, trades,
    )

    return cash, positions, {
        "signal_date": signal_date,
        "settlement_date": settlement_date,
        "selected": list(selected),
        "sale_proceeds": sale_proceeds,
        "target_total": pretrade_value,
        "target_weight": target_weight,
    }


def execute_settlement_stage(
    event,
    cash,
    positions,
    tapes,
    slippage_bps,
    fee_per_order,
    trades,
):
    cash += event["sale_proceeds"]
    return buy_shortfalls(
        event["signal_date"], event["settlement_date"], event["selected"],
        cash, event["target_total"], event["target_weight"], positions, tapes,
        slippage_bps, fee_per_order, trades,
    ), positions


def buy_shortfalls(
    signal_date,
    trade_date,
    selected,
    cash,
    target_total,
    target_weight,
    positions,
    tapes,
    slippage_bps,
    fee_per_order,
    trades,
):
    needs = []
    for ticker in selected:
        raw = price_on(tapes.get(ticker), trade_date, 1)
        if raw is None:
            continue
        current = positions.get(ticker, 0.0) * raw
        need = max(0.0, target_total * target_weight - current)
        if need > fee_per_order:
            needs.append((ticker, raw, need))
    total_need = sum(item[2] for item in needs)
    if total_need <= 0 or cash <= fee_per_order:
        return cash
    scale = min(1.0, cash / (total_need + fee_per_order * len(needs)))
    for ticker, raw, need in needs:
        spend = need * scale
        buy_price = raw * (1.0 + slippage_bps / 10000.0)
        available = min(spend, max(0.0, cash - fee_per_order))
        shares = available / buy_price
        if shares <= 1e-12:
            continue
        gross = shares * buy_price
        cash -= gross + fee_per_order
        positions[ticker] = positions.get(ticker, 0.0) + shares
        trades.append({
            "signal_date": signal_date, "trade_date": trade_date,
            "ticker": ticker, "side": "BUY", "shares": shares,
            "price": buy_price, "gross_value": gross,
            "fee": fee_per_order, "settlement_date": trade_date,
        })
    return max(0.0, cash)


def benchmark_path(calendar, tape, cutoffs, start, end):
    requested_trade = next_date(calendar, cutoffs[0])
    entry_position = bisect.bisect_left(tape["dates"], requested_trade)
    if entry_position >= len(tape["dates"]):
        raise RuntimeError("benchmark has no observations in evaluation window")
    first_trade = tape["dates"][entry_position]
    entry = price_on(tape, first_trade, 1)
    if entry is None:
        raise RuntimeError("benchmark has no execution price on {}".format(first_trade))
    shares = INITIAL_CASH / entry
    path = []
    for date in calendar["dates"]:
        if max(start, first_trade) <= date <= end:
            close = latest_close_on_or_before(tape, date)
            value = shares * close
            path.append((date, value))
    return path


def eligible_universe_path(cutoffs, coverage_rows, scores_by_cutoff, tapes):
    value = INITIAL_CASH
    path = []
    for index, cutoff in enumerate(cutoffs):
        if index:
            previous = cutoffs[index - 1]
            returns = []
            for _, ticker in scores_by_cutoff[previous]:
                start = latest_close_on_or_before(tapes[ticker], previous)
                end = latest_close_on_or_before(tapes[ticker], cutoff)
                if start is not None and end is not None and start > 0:
                    returns.append(end / start - 1.0)
            if returns:
                value *= 1.0 + statistics.mean(returns)
        path.append((cutoff, value))
    return path


def drawdown(path):
    peak = -math.inf
    worst = 0.0
    for _, value in path:
        peak = max(peak, value)
        if peak > 0:
            worst = min(worst, value / peak - 1.0)
    return worst


def maximum_time_underwater_days(path):
    peak = -math.inf
    peak_date = None
    longest = 0
    for date, value in path:
        if value >= peak:
            peak = value
            peak_date = date
        elif peak_date is not None:
            days = (
                datetime.strptime(date, "%Y-%m-%d")
                - datetime.strptime(peak_date, "%Y-%m-%d")
            ).days
            longest = max(longest, days)
    return longest


def annualized_metrics(path, periods_per_year=252.0):
    if len(path) < 2:
        return {}
    start_date, start_value = path[0]
    end_date, end_value = path[-1]
    years = max(1.0 / 365.25, (
        datetime.strptime(end_date, "%Y-%m-%d")
        - datetime.strptime(start_date, "%Y-%m-%d")
    ).days / 365.25)
    returns = [
        path[index][1] / path[index - 1][1] - 1.0
        for index in range(1, len(path))
        if path[index - 1][1] > 0
    ]
    volatility = (
        statistics.stdev(returns) * math.sqrt(periods_per_year)
        if len(returns) > 1 else 0.0
    )
    cagr = (end_value / start_value) ** (1.0 / years) - 1.0
    return {
        "start_date": start_date,
        "end_date": end_date,
        "start_value": start_value,
        "terminal_value": end_value,
        "total_return": end_value / start_value - 1.0,
        "cagr": cagr,
        "annualized_volatility": volatility,
        "sharpe_0rf": cagr / volatility if volatility > 0 else None,
        "maximum_drawdown": drawdown(path),
        "maximum_time_underwater_days": maximum_time_underwater_days(path),
    }


def calendar_year_returns(series_name, path):
    by_year = defaultdict(list)
    for date, value in path:
        by_year[date[:4]].append((date, value))
    rows = []
    prior = path[0][1]
    for year in sorted(by_year):
        end_date, end_value = by_year[year][-1]
        rows.append({
            "series": series_name,
            "year": year,
            "end_date": end_date,
            "start_value": prior,
            "end_value": end_value,
            "return": end_value / prior - 1.0 if prior > 0 else None,
            "profit": end_value - prior,
        })
        prior = end_value
    return rows


def month_ends(path):
    result = {}
    for date, value in path:
        result[date[:7]] = (date, value)
    return [result[key] for key in sorted(result)]


def rolling_excess(strategy_path, benchmark_path, benchmark_name):
    strategy = {date[:7]: (date, value) for date, value in month_ends(strategy_path)}
    benchmark = {date[:7]: (date, value) for date, value in month_ends(benchmark_path)}
    months = sorted(set(strategy) & set(benchmark))
    rows = []
    for index in range(12, len(months)):
        start_month = months[index - 12]
        end_month = months[index]
        strategy_return = (
            strategy[end_month][1] / strategy[start_month][1] - 1.0
        )
        benchmark_return = (
            benchmark[end_month][1] / benchmark[start_month][1] - 1.0
        )
        rows.append({
            "end_date": strategy[end_month][0],
            "benchmark": benchmark_name,
            "strategy_return": strategy_return,
            "benchmark_return": benchmark_return,
            "excess_return": strategy_return - benchmark_return,
        })
    return rows


def ticker_profit_concentration(trades, positions, tapes, end_date):
    contributions = defaultdict(float)
    for trade in trades:
        signed = trade["gross_value"] * (1.0 if trade["side"] == "SELL" else -1.0)
        contributions[trade["ticker"]] += signed - trade["fee"]
    for ticker, shares in positions.items():
        contributions[ticker] += shares * latest_close_on_or_before(
            tapes[ticker], end_date
        )
    total_profit = sum(contributions.values())
    return [
        {
            "ticker": ticker,
            "profit_contribution": value,
            "share_of_total_profit": (
                value / total_profit if total_profit > 0 else None
            ),
        }
        for ticker, value in sorted(
            contributions.items(), key=lambda item: (-item[1], item[0])
        )
    ]


def file_sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(path, rows):
    rows = list(rows)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run(args):
    if args.slippage_bps < 0 or args.fee_per_order < 0:
        raise ValueError("cost inputs must be non-negative")
    membership_dates, memberships = load_memberships()
    gap_symbols = load_gap_symbols()
    local = {path.stem for path in FEATURE_ROOT.glob("*/*.csv")}
    spy = load_tape("SPY")
    if spy is None:
        raise RuntimeError("SPY tape is required")
    cutoffs = monthly_cutoffs(spy, args.evaluation_start, args.evaluation_end)
    if not cutoffs:
        raise RuntimeError("evaluation window contains no decision cutoffs")
    required = set(["SPY", "VFMO"])
    for cutoff in cutoffs:
        _, members = resolve_membership(cutoff, membership_dates, memberships)
        required.update(normalize_ticker(ticker) for ticker in members)
    tapes = {ticker: load_tape(ticker) for ticker in sorted(required & local)}
    tapes = {ticker: tape for ticker, tape in tapes.items() if tape is not None}
    spy = tapes["SPY"]

    cash = INITIAL_CASH
    positions = {}
    trades = []
    daily_path = []
    coverage = []
    selections = []
    scores_by_cutoff = {}
    pending_by_date = {}
    settlements_by_date = defaultdict(list)
    unsettled_cash = 0.0
    regime_rows = []

    for cutoff in cutoffs:
        snapshot_date, members = resolve_membership(
            cutoff, membership_dates, memberships
        )
        selected, scores, exclusions = select_targets(
            cutoff, members, tapes, gap_symbols
        )
        if len(selected) != TARGET_COUNT:
            raise RuntimeError("fewer than ten eligible targets on {}".format(cutoff))
        market_close = price_on(spy, cutoff, 2)
        market_sma = price_on(spy, cutoff, 3)
        gate_open = True
        if args.market_sma_window is not None:
            if market_close is None or market_sma is None:
                raise RuntimeError("SPY SMA200 unavailable on {}".format(cutoff))
            gate_open = market_close >= market_sma
        regime_rows.append({
            "cutoff": cutoff,
            "spy_adjusted_close": market_close,
            "spy_sma_200": market_sma,
            "gate_open": gate_open,
        })
        if not gate_open:
            selected = []
        scores_by_cutoff[cutoff] = scores
        coverage.append({
            "cutoff": cutoff,
            "membership_snapshot": snapshot_date,
            "membership_count": len(set(members)),
            "eligible_count": len(scores),
            "coverage": len(scores) / float(len(set(members))),
            "exclusions": json.dumps(exclusions, sort_keys=True),
        })
        for rank, ticker in enumerate(selected, 1):
            selections.append({
                "cutoff": cutoff, "rank": rank, "ticker": ticker,
                "momentum_12_1": dict((name, score) for score, name in scores)[ticker],
                "target_weight": 1.0 / TARGET_COUNT,
            })
        sell_date = next_date(spy, cutoff)
        settlement_date = next_date(spy, cutoff, 2)
        if sell_date is not None and settlement_date is not None:
            pending_by_date[sell_date] = (
                cutoff, settlement_date, list(selected)
            )

    cutoff_set = set(cutoffs)
    for date in spy["dates"]:
        if date < args.evaluation_start or date > args.evaluation_end:
            continue
        if date in pending_by_date:
            signal_date, settlement_date, selected = pending_by_date[date]
            cash, positions, settlement = execute_sale_stage(
                signal_date, date, settlement_date, selected, cash, positions,
                tapes, args.slippage_bps, args.fee_per_order, trades,
            )
            settlements_by_date[settlement_date].append(settlement)
            unsettled_cash += settlement["sale_proceeds"]
        for settlement in settlements_by_date.get(date, []):
            unsettled_cash -= settlement["sale_proceeds"]
            cash, positions = execute_settlement_stage(
                settlement, cash, positions, tapes, args.slippage_bps,
                args.fee_per_order, trades,
            )
        daily_path.append((
            date,
            marked_value(cash, positions, tapes, date) + unsettled_cash,
        ))

    spy_path = benchmark_path(
        spy, spy, cutoffs, args.evaluation_start, args.evaluation_end
    )
    vfmo_path = benchmark_path(
        spy, tapes["VFMO"], cutoffs, args.evaluation_start, args.evaluation_end
    )
    universe_path = eligible_universe_path(
        cutoffs, coverage, scores_by_cutoff, tapes
    )
    metrics = [
        {"series": "strategy", **annualized_metrics(daily_path)},
        {"series": "SPY", **annualized_metrics(spy_path)},
        {"series": "VFMO", **annualized_metrics(vfmo_path)},
        {"series": "equal_weight_eligible_universe",
         **annualized_metrics(universe_path, periods_per_year=12.0)},
    ]
    calendar_rows = []
    for name, path in (
        ("strategy", daily_path),
        ("SPY", spy_path),
        ("VFMO", vfmo_path),
        ("equal_weight_eligible_universe", universe_path),
    ):
        calendar_rows.extend(calendar_year_returns(name, path))
    rolling_rows = []
    for name, path in (
        ("SPY", spy_path),
        ("VFMO", vfmo_path),
        ("equal_weight_eligible_universe", universe_path),
    ):
        rolling_rows.extend(rolling_excess(daily_path, path, name))
    ticker_concentration = ticker_profit_concentration(
        trades, positions, tapes, args.evaluation_end
    )
    gross_turnover = sum(row["gross_value"] for row in trades)
    return {
        "metrics": metrics,
        "path": daily_path,
        "spy_path": spy_path,
        "vfmo_path": vfmo_path,
        "universe_path": universe_path,
        "coverage": coverage,
        "selections": selections,
        "trades": trades,
        "regimes": regime_rows,
        "calendar_years": calendar_rows,
        "rolling_excess": rolling_rows,
        "ticker_concentration": ticker_concentration,
        "implementation": [{
            "trade_count": len(trades),
            "gross_traded_value": gross_turnover,
            "gross_turnover_over_initial_capital": gross_turnover / INITIAL_CASH,
            "total_fees": sum(row["fee"] for row in trades),
        }],
        "config": {
            "evaluation_start": args.evaluation_start,
            "evaluation_end": args.evaluation_end,
            "warmup_start": args.warmup_start,
            "initial_cash": INITIAL_CASH,
            "target_count": TARGET_COUNT,
            "slippage_bps": args.slippage_bps,
            "fee_per_order": args.fee_per_order,
            "market_sma_window": args.market_sma_window,
            "membership_sha256": file_sha256(MEMBERSHIP_PATH),
            "integrity_sha256": file_sha256(INTEGRITY_PATH),
            "signal": "adj_close[t-21]/adj_close[t-252]-1",
            "signal_cutoff": "last completed monthly session",
            "fill": "next-session adjusted open",
            "settlement": "T+1 sale proceeds",
        },
    }


def main(argv=None):
    args = parse_args(argv)
    result = run(args)
    config_text = json.dumps(result["config"], sort_keys=True)
    digest = hashlib.sha256(config_text.encode()).hexdigest()[:8]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%SZ")
    output_root = (
        args.output_root
        or (GATED_OUTPUT_ROOT if args.market_sma_window else OUTPUT_ROOT)
    )
    output = args.output_dir or output_root / (
        "{}__post-validation-confirmation__{}".format(stamp, digest)
    )
    output.mkdir(parents=True, exist_ok=False)
    (output / "configuration.json").write_text(
        json.dumps(result["config"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_csv(output / "summary.csv", result["metrics"])
    write_csv(output / "equity-curve.csv", [
        {"date": date, "value": value} for date, value in result["path"]
    ])
    write_csv(output / "spy-equity-curve.csv", [
        {"date": date, "value": value} for date, value in result["spy_path"]
    ])
    write_csv(output / "vfmo-equity-curve.csv", [
        {"date": date, "value": value} for date, value in result["vfmo_path"]
    ])
    write_csv(output / "eligible-universe-equity-curve.csv", [
        {"date": date, "value": value} for date, value in result["universe_path"]
    ])
    write_csv(output / "coverage.csv", result["coverage"])
    write_csv(output / "selections.csv", result["selections"])
    write_csv(output / "trades.csv", result["trades"])
    write_csv(output / "market-regimes.csv", result["regimes"])
    write_csv(output / "calendar-year-returns.csv", result["calendar_years"])
    write_csv(output / "rolling-12-month-excess.csv", result["rolling_excess"])
    write_csv(output / "ticker-profit-concentration.csv",
              result["ticker_concentration"])
    write_csv(output / "implementation-summary.csv", result["implementation"])
    try:
        display_path = output.relative_to(ROOT)
    except ValueError:
        display_path = output
    print(display_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
