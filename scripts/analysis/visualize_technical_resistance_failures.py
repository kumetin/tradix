#!/usr/bin/env python3
"""Visualize failed Technical Resistance Runner setups."""

from __future__ import annotations

import csv
import calendar
import sys
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
import historical_setup_evaluator_snapshot as snapshot


ARTIFACT_ROOT = (
    ROOT
    / "artifacts/stock/backtests/strategies/technical-resistance-runner/robustness"
)
OUTPUT = ARTIFACT_ROOT / "filter-discovery"
COLORS = {1: "#4c78a8", 2: "#59a14f", 3: "#e15759", 4: "#f28e2b", 5: "#b07aa1"}


def read_csv(path):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def load_failures():
    failures = []
    for universe in range(1, 6):
        directory = ARTIFACT_ROOT / "universe-{}".format(universe) / "full_at_5_21"
        predictions = {
            (row["entry_date"], row["ticker"]): row
            for row in read_csv(directory / "predictions.csv")
            if row["action"] == "enter"
        }
        for trade in read_csv(directory / "trades.csv"):
            trade_return = float(trade["return_pct"])
            if trade_return >= 0:
                continue
            prediction = predictions[(trade["entry_date"], trade["ticker"])]
            rows = snapshot.load_rows(ROOT / "data/stock/features/daily", trade["ticker"])
            setup_start = months_before(trade["entry_date"], 6)
            pre_entry_path = [
                row
                for row in rows
                if setup_start <= row["date"] <= trade["entry_date"]
            ]
            path = [
                row
                for row in rows
                if trade["entry_date"] <= row["date"] <= trade["exit_date"]
            ]
            failures.append(
                {
                    "universe": universe,
                    "ticker": trade["ticker"],
                    "entry_date": trade["entry_date"],
                    "exit_date": trade["exit_date"],
                    "entry_price": float(trade["entry_price"]),
                    "return_pct": trade_return,
                    "score": float(trade["score"]),
                    "support": float(prediction["support"]),
                    "target": float(trade["first_target"]),
                    "resistance": float(prediction["target"]),
                    "path": path,
                    "pre_entry_path": pre_entry_path,
                }
            )
    return failures


def normalized_series(failure, field):
    entry = failure["entry_price"]
    return [
        (snapshot.as_float(row[field]) / entry - 1.0) * 100.0
        for row in failure["path"]
    ]


def plot_overview(failures):
    figure, axis = plt.subplots(figsize=(14, 8))
    for failure in failures:
        closes = normalized_series(failure, "adj_close")
        axis.plot(
            range(len(closes)),
            closes,
            color=COLORS[failure["universe"]],
            alpha=0.42,
            linewidth=1.2,
        )
        axis.scatter(
            len(closes) - 1,
            closes[-1],
            color=COLORS[failure["universe"]],
            s=18,
            alpha=0.75,
        )
    axis.axhline(5.21, color="#2ca02c", linestyle="--", linewidth=2, label="+5.21% target")
    axis.axhline(0, color="#333333", linewidth=1)
    axis.set_title("All Failed +5.21% Setups: Entry-to-Exit Closing Paths", fontsize=16, weight="bold")
    axis.set_xlabel("Trading sessions after entry")
    axis.set_ylabel("Adjusted close return from entry (%)")
    axis.grid(alpha=0.18)
    handles = [
        Line2D([0], [0], color=COLORS[number], lw=3, label="Universe {}".format(number))
        for number in range(1, 6)
    ]
    handles.append(Line2D([0], [0], color="#2ca02c", lw=2, ls="--", label="+5.21% target"))
    axis.legend(handles=handles, ncol=3, frameon=False, loc="lower left")
    figure.text(
        0.99,
        0.01,
        "{} completed losing trades; adjusted daily closes; no stop-loss.".format(len(failures)),
        ha="right",
        fontsize=9,
        color="#555555",
    )
    figure.tight_layout(rect=(0, 0.025, 1, 1))
    figure.savefig(OUTPUT / "failed-setups-overview.png", dpi=180)
    plt.close(figure)


def plot_worst(failures):
    worst = sorted(failures, key=lambda row: row["return_pct"])[:9]
    figure, axes = plt.subplots(3, 3, figsize=(16, 12), sharex=True, sharey=True)
    for axis, failure in zip(axes.flat, worst):
        x = list(range(len(failure["path"])))
        lows = normalized_series(failure, "adj_low")
        highs = normalized_series(failure, "adj_high")
        closes = normalized_series(failure, "adj_close")
        support_return = (failure["support"] / failure["entry_price"] - 1.0) * 100.0
        axis.fill_between(x, lows, highs, color=COLORS[failure["universe"]], alpha=0.15)
        axis.plot(x, closes, color=COLORS[failure["universe"]], linewidth=1.7)
        axis.axhline(5.21, color="#2ca02c", linestyle="--", linewidth=1.3)
        axis.axhline(0, color="#333333", linewidth=0.9)
        axis.axhline(support_return, color="#9467bd", linestyle=":", linewidth=1.2)
        axis.scatter(x[-1], closes[-1], color="#b22222", s=28, zorder=4)
        axis.set_title(
            "{} · U{} · {:+.1f}%".format(
                failure["ticker"], failure["universe"], failure["return_pct"]
            ),
            fontsize=12,
            weight="bold",
        )
        axis.text(
            0.02,
            0.03,
            "{} → {}\nscore {:.1f} · support {:+.1f}%".format(
                failure["entry_date"],
                failure["exit_date"],
                failure["score"],
                support_return,
            ),
            transform=axis.transAxes,
            fontsize=8,
            va="bottom",
            color="#444444",
        )
        axis.grid(alpha=0.15)
    figure.suptitle(
        "Nine Worst Failed Setups: Adjusted Intraday Range and Closing Path",
        fontsize=17,
        weight="bold",
    )
    figure.text(0.5, 0.035, "Trading sessions after entry", ha="center")
    figure.text(0.012, 0.5, "Return from entry (%)", va="center", rotation="vertical")
    handles = [
        Line2D([0], [0], color="#555555", lw=2, label="Adjusted close"),
        Line2D([0], [0], color="#2ca02c", lw=1.5, ls="--", label="+5.21% target"),
        Line2D([0], [0], color="#9467bd", lw=1.5, ls=":", label="Setup support"),
    ]
    figure.legend(handles=handles, ncol=3, loc="lower center", frameon=False)
    figure.tight_layout(rect=(0.02, 0.05, 1, 0.96))
    figure.savefig(OUTPUT / "worst-failing-setups.png", dpi=180)
    plt.close(figure)


def normalized_pre_entry(failure, field):
    entry = failure["entry_price"]
    return [
        (
            (snapshot.as_float(row[field]) / entry - 1.0) * 100.0
            if snapshot.as_float(row.get(field)) is not None
            else None
        )
        for row in failure["pre_entry_path"]
    ]


def plot_pre_entry_overview(failures):
    figure, axis = plt.subplots(figsize=(14, 8))
    for failure in failures:
        closes = normalized_pre_entry(failure, "adj_close")
        x = list(range(-len(closes) + 1, 1))
        axis.plot(
            x,
            closes,
            color=COLORS[failure["universe"]],
            alpha=0.42,
            linewidth=1.2,
        )
        axis.scatter(0, closes[-1], color=COLORS[failure["universe"]], s=18, alpha=0.75)
    axis.axvline(0, color="#111111", linewidth=1.4)
    axis.axhline(0, color="#333333", linewidth=1)
    axis.set_title(
        "All Failed Setups: Six-Month Price Path Before Entry",
        fontsize=16,
        weight="bold",
    )
    axis.set_xlabel("Trading sessions relative to entry")
    axis.set_ylabel("Adjusted close return relative to entry price (%)")
    axis.grid(alpha=0.18)
    handles = [
        Line2D([0], [0], color=COLORS[number], lw=3, label="Universe {}".format(number))
        for number in range(1, 6)
    ]
    handles.append(Line2D([0], [0], color="#111111", lw=1.5, label="Entry day"))
    axis.legend(handles=handles, ncol=3, frameon=False, loc="upper left")
    figure.tight_layout()
    figure.savefig(OUTPUT / "failed-setups-six-month-pre-entry-overview.png", dpi=180)
    plt.close(figure)


def plot_worst_pre_entry(failures):
    worst = sorted(failures, key=lambda row: row["return_pct"])[:9]
    figure, axes = plt.subplots(3, 3, figsize=(16, 12), sharex=True, sharey=True)
    for axis, failure in zip(axes.flat, worst):
        rows = failure["pre_entry_path"]
        x = list(range(-len(rows) + 1, 1))
        closes = normalized_pre_entry(failure, "adj_close")
        sma20 = normalized_pre_entry(failure, "sma_20")
        sma50 = normalized_pre_entry(failure, "sma_50")
        sma150 = normalized_pre_entry(failure, "sma_150")
        support_return = (failure["support"] / failure["entry_price"] - 1.0) * 100.0
        resistance_return = (failure["resistance"] / failure["entry_price"] - 1.0) * 100.0
        axis.plot(x, closes, color=COLORS[failure["universe"]], linewidth=2.0)
        axis.plot(x, sma20, color="#4c78a8", linewidth=1.0, alpha=0.85)
        axis.plot(x, sma50, color="#f28e2b", linewidth=1.1, alpha=0.9)
        axis.plot(x, sma150, color="#777777", linewidth=1.2, alpha=0.9)
        axis.axhline(support_return, color="#9467bd", linestyle=":", linewidth=1.2)
        axis.axhline(resistance_return, color="#2ca02c", linestyle="--", linewidth=1.2)
        axis.axhline(0, color="#333333", linewidth=0.8)
        axis.axvline(0, color="#111111", linewidth=1.0)
        axis.scatter(0, closes[-1], color="#111111", s=30, zorder=5)
        axis.set_title(
            "{} · U{} · later {:+.1f}%".format(
                failure["ticker"], failure["universe"], failure["return_pct"]
            ),
            fontsize=12,
            weight="bold",
        )
        axis.text(
            0.02,
            0.03,
            "entry {} · score {:.1f}\nsupport {:+.1f}% · resistance {:+.1f}%".format(
                failure["entry_date"],
                failure["score"],
                support_return,
                resistance_return,
            ),
            transform=axis.transAxes,
            fontsize=8,
            va="bottom",
            color="#444444",
        )
        axis.grid(alpha=0.15)
    figure.suptitle(
        "Nine Worst Failures: The 126-Session Setup Before Entry",
        fontsize=17,
        weight="bold",
    )
    figure.text(0.5, 0.035, "Trading sessions relative to entry", ha="center")
    figure.text(0.012, 0.5, "Return relative to entry price (%)", va="center", rotation="vertical")
    handles = [
        Line2D([0], [0], color="#555555", lw=2, label="Adjusted close"),
        Line2D([0], [0], color="#4c78a8", lw=1.2, label="SMA20"),
        Line2D([0], [0], color="#f28e2b", lw=1.2, label="SMA50"),
        Line2D([0], [0], color="#777777", lw=1.2, label="SMA150"),
        Line2D([0], [0], color="#9467bd", lw=1.5, ls=":", label="Support"),
        Line2D([0], [0], color="#2ca02c", lw=1.5, ls="--", label="Resistance"),
    ]
    figure.legend(handles=handles, ncol=6, loc="lower center", frameon=False)
    figure.tight_layout(rect=(0.02, 0.05, 1, 0.96))
    figure.savefig(OUTPUT / "worst-failing-setups-six-month-pre-entry.png", dpi=180)
    plt.close(figure)


def months_before(date_text, months):
    value = date.fromisoformat(date_text)
    month_index = value.year * 12 + value.month - 1 - months
    year, zero_based_month = divmod(month_index, 12)
    month = zero_based_month + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day).isoformat()


def plot_setup_candles(failure):
    start_date = months_before(failure["entry_date"], 6)
    rows = [
        row
        for row in failure["pre_entry_path"]
        if start_date <= row["date"] <= failure["entry_date"]
    ]
    figure, axis = plt.subplots(figsize=(14, 8))
    for index, row in enumerate(rows):
        open_price = snapshot.as_float(row["adj_open"])
        high = snapshot.as_float(row["adj_high"])
        low = snapshot.as_float(row["adj_low"])
        close = snapshot.as_float(row["adj_close"])
        color = "#2a9d8f" if close >= open_price else "#e76f51"
        axis.vlines(index, low, high, color=color, linewidth=0.8, alpha=0.9)
        body_bottom = min(open_price, close)
        body_height = max(abs(close - open_price), max(close * 0.0005, 0.01))
        axis.add_patch(
            Rectangle(
                (index - 0.32, body_bottom),
                0.64,
                body_height,
                facecolor=color,
                edgecolor=color,
                linewidth=0.5,
            )
        )
    x = list(range(len(rows)))
    axis.plot(x, [snapshot.as_float(row["sma_20"]) for row in rows], color="#4c78a8", lw=1.2, label="SMA20")
    axis.plot(x, [snapshot.as_float(row["sma_50"]) for row in rows], color="#f28e2b", lw=1.3, label="SMA50")
    axis.plot(x, [snapshot.as_float(row["sma_150"]) for row in rows], color="#666666", lw=1.4, label="SMA150")
    axis.axhline(failure["support"], color="#9467bd", ls=":", lw=1.6, label="Setup support")
    axis.axhline(failure["resistance"], color="#2ca02c", ls="--", lw=1.6, label="Setup resistance")
    entry_x = len(rows) - 1
    axis.axvline(entry_x, color="#111111", lw=1.2)
    axis.scatter(
        entry_x,
        failure["entry_price"],
        color="#111111",
        s=55,
        zorder=6,
        label="Next-open entry",
    )
    tick_step = max(len(rows) // 6, 1)
    ticks = list(range(0, len(rows), tick_step))
    if ticks[-1] != entry_x:
        ticks.append(entry_x)
    axis.set_xticks(ticks)
    axis.set_xticklabels([rows[index]["date"] for index in ticks], rotation=30, ha="right")
    axis.set_xlim(-1, len(rows))
    axis.set_title(
        "{} · Universe {} · Six-Month Setup Ending at Entry\n"
        "entry {} at {:.2f} · score {:.1f} · eventual return {:+.1f}%".format(
            failure["ticker"],
            failure["universe"],
            failure["entry_date"],
            failure["entry_price"],
            failure["score"],
            failure["return_pct"],
        ),
        fontsize=16,
        weight="bold",
    )
    axis.set_xlabel("Date")
    axis.set_ylabel("Adjusted price")
    axis.grid(alpha=0.16)
    axis.legend(ncol=3, frameon=False, loc="best")
    figure.text(
        0.99,
        0.01,
        "Window: {} through {} ({} trading sessions)".format(
            start_date, failure["entry_date"], len(rows)
        ),
        ha="right",
        fontsize=9,
        color="#555555",
    )
    figure.tight_layout(rect=(0, 0.025, 1, 1))
    return figure


def plot_all_individual_setups(failures):
    chart_directory = OUTPUT / "failed-setup-charts"
    chart_directory.mkdir(parents=True, exist_ok=True)
    pdf_path = OUTPUT / "all-failing-setups-six-month-to-entry.pdf"
    ordered = sorted(failures, key=lambda row: (row["entry_date"], row["ticker"]))
    with PdfPages(str(pdf_path)) as pdf:
        for failure in ordered:
            figure = plot_setup_candles(failure)
            filename = "{}-{}-u{}.png".format(
                failure["entry_date"], failure["ticker"], failure["universe"]
            )
            figure.savefig(chart_directory / filename, dpi=160)
            pdf.savefig(figure)
            plt.close(figure)


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    failures = load_failures()
    plot_overview(failures)
    plot_worst(failures)
    plot_pre_entry_overview(failures)
    plot_worst_pre_entry(failures)
    plot_all_individual_setups(failures)
    print("Rendered {} failures to {}".format(len(failures), OUTPUT))


if __name__ == "__main__":
    main()
