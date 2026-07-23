#!/usr/bin/env python3
"""Render 12-month setup/outcome charts for every completed baseline trade."""

from __future__ import annotations

import calendar
import argparse
import csv
import sys
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
import historical_setup_evaluator_snapshot as snapshot


ARTIFACT_ROOT = (
    ROOT
    / "artifacts/stock/backtests/strategies/technical-resistance-runner/robustness"
)
OUTPUT = ARTIFACT_ROOT / "filter-discovery" / "twelve-month-trade-charts"


def read_csv(path):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def shift_months(date_text, offset):
    value = date.fromisoformat(date_text)
    month_index = value.year * 12 + value.month - 1 + offset
    year, zero_based_month = divmod(month_index, 12)
    month = zero_based_month + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day).isoformat()


def load_trades():
    loaded = []
    histories = {}
    for universe in range(1, 6):
        directory = ARTIFACT_ROOT / "universe-{}".format(universe) / "full_at_5_21"
        predictions = {
            (row["entry_date"], row["ticker"]): row
            for row in read_csv(directory / "predictions.csv")
            if row["action"] == "enter"
        }
        for trade in read_csv(directory / "trades.csv"):
            key = (trade["entry_date"], trade["ticker"])
            prediction = predictions.get(key)
            if prediction is None:
                continue
            ticker = trade["ticker"]
            histories.setdefault(
                ticker,
                snapshot.load_rows(ROOT / "data/stock/features/daily", ticker),
            )
            entry_index = next(
                index
                for index, row in enumerate(histories[ticker])
                if row["date"] == trade["entry_date"]
            )
            rows = histories[ticker][
                max(0, entry_index - 126) : entry_index + 127
            ]
            window_start = rows[0]["date"]
            window_end = rows[-1]["date"]
            loaded.append(
                {
                    "universe": universe,
                    "ticker": ticker,
                    "entry_date": trade["entry_date"],
                    "exit_date": trade["exit_date"],
                    "entry_price": float(trade["entry_price"]),
                    "exit_price": float(trade["exit_price"]),
                    "return_pct": float(trade["return_pct"]),
                    "score": float(trade["score"]),
                    "support": float(prediction["support"]),
                    "resistance": float(prediction["target"]),
                    "profit_target": float(trade["first_target"]),
                    "successful": float(trade["return_pct"]) > 0,
                    "window_start": window_start,
                    "window_end": window_end,
                    "rows": rows,
                }
            )
    return loaded


def render_trade(trade):
    rows = trade["rows"]
    figure, axis = plt.subplots(figsize=(15, 8))
    for index, row in enumerate(rows):
        open_price = snapshot.as_float(row["adj_open"])
        high = snapshot.as_float(row["adj_high"])
        low = snapshot.as_float(row["adj_low"])
        close = snapshot.as_float(row["adj_close"])
        color = "#2a9d8f" if close >= open_price else "#e76f51"
        axis.vlines(index, low, high, color=color, linewidth=0.65, alpha=0.8)
        axis.add_patch(
            Rectangle(
                (index - 0.30, min(open_price, close)),
                0.60,
                max(abs(close - open_price), max(close * 0.0004, 0.01)),
                facecolor=color,
                edgecolor=color,
                linewidth=0.4,
            )
        )
    x = list(range(len(rows)))
    axis.plot(x, [snapshot.as_float(row["sma_20"]) for row in rows], color="#4c78a8", lw=1.0, label="SMA20")
    axis.plot(x, [snapshot.as_float(row["sma_50"]) for row in rows], color="#f28e2b", lw=1.1, label="SMA50")
    axis.plot(x, [snapshot.as_float(row["sma_150"]) for row in rows], color="#666666", lw=1.2, label="SMA150")

    date_index = {row["date"]: index for index, row in enumerate(rows)}
    entry_x = date_index[trade["entry_date"]]
    exit_x = date_index.get(trade["exit_date"])
    axis.axvline(entry_x, color="#111111", lw=1.5, label="Entry")
    axis.axhline(trade["profit_target"], color="#1b9e3c", ls="--", lw=1.3, label="+5.21% target")
    axis.axhline(trade["support"], color="#9467bd", ls=":", lw=1.3, label="Setup support")
    axis.axhline(trade["resistance"], color="#17a2a4", ls="-.", lw=1.3, label="Setup resistance")
    axis.scatter(entry_x, trade["entry_price"], color="#111111", s=50, zorder=6)
    if exit_x is not None:
        axis.axvline(exit_x, color="#b22222", lw=1.0, alpha=0.7)
        axis.scatter(exit_x, trade["exit_price"], color="#b22222", s=55, zorder=6, label="Exit")

    tick_step = max(len(rows) // 8, 1)
    ticks = list(range(0, len(rows), tick_step))
    for special in (entry_x, exit_x):
        if special is not None and special not in ticks:
            ticks.append(special)
    ticks = sorted(set(ticks))
    axis.set_xticks(ticks)
    axis.set_xticklabels([rows[index]["date"] for index in ticks], rotation=30, ha="right")
    axis.set_xlim(-1, len(rows))
    result = "SUCCESS" if trade["successful"] else "FAILURE"
    axis.set_title(
        "{} · U{} · {} · return {:+.1f}%\n"
        "entry {} at {:.2f} · exit {} at {:.2f} · score {:.1f}".format(
            trade["ticker"],
            trade["universe"],
            result,
            trade["return_pct"],
            trade["entry_date"],
            trade["entry_price"],
            trade["exit_date"],
            trade["exit_price"],
            trade["score"],
        ),
        fontsize=15,
        weight="bold",
    )
    axis.set_xlabel("Date — entry is the black vertical line")
    axis.set_ylabel("Adjusted price")
    axis.grid(alpha=0.15)
    axis.legend(ncol=4, frameon=False, loc="best")
    figure.text(
        0.99,
        0.01,
        "{} through {} · {} trading sessions".format(
            trade["window_start"], trade["window_end"], len(rows)
        ),
        ha="right",
        fontsize=9,
        color="#555555",
    )
    figure.tight_layout(rect=(0, 0.025, 1, 1))
    return figure


def render_collection(trades, label):
    pdf_path = OUTPUT / "{}-trades-12-month-entry-centered.pdf".format(label)
    with PdfPages(str(pdf_path)) as pdf:
        for trade in sorted(trades, key=lambda row: (row["entry_date"], row["ticker"])):
            figure = render_trade(trade)
            pdf.savefig(figure)
            plt.close(figure)
    return pdf_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--collection",
        choices=("successful", "failing", "all"),
        default="all",
    )
    args = parser.parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    trades = load_trades()
    successful = [trade for trade in trades if trade["successful"]]
    failing = [trade for trade in trades if not trade["successful"]]
    if args.collection in ("successful", "all"):
        success_pdf = render_collection(successful, "successful")
        print("Rendered {} successful trades to {}".format(len(successful), success_pdf))
    if args.collection in ("failing", "all"):
        failure_pdf = render_collection(failing, "failing")
        print("Rendered {} failing trades to {}".format(len(failing), failure_pdf))


if __name__ == "__main__":
    main()
