#!/usr/bin/env python3
"""Render a lower-risk swing setup row as a dependency-free SVG chart."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import html
import math
import re
import sys
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[2]
FEATURE_ROOT = ROOT / "data/stock/features/daily"
DEFAULT_OUTPUT_ROOT = ROOT / "data/stock/setup-visualizations"
DEFAULT_DAYS = 252
KNOWN_COLUMNS = [
    "Rank",
    "Ticker",
    "Current Price",
    "Setup Type",
    "Key Support",
    "Key Resistance",
    "Analyst Support",
    "Buy Limit Order",
    "Trailing Stop",
    "Take Profit",
    "Reward/Risk",
    "Setup Status",
    "Confidence",
]
SMA_COLUMNS = {
    20: "sma_20",
    50: "sma_50",
    100: "sma_100",
    150: "sma_150",
    200: "sma_200",
}


class Setup:
    def __init__(self, cells: dict[str, str], raw: str) -> None:
        self.cells = cells
        self.raw = raw
        self.ticker = self._ticker()
        self.current_price = first_money(cells.get("Current Price", ""))
        self.buy_prices = money_values(cells.get("Buy Limit Order", ""))
        self.buy_limit = self.buy_prices[0] if self.buy_prices else None
        self.trailing_stop_amount = first_money(cells.get("Trailing Stop", ""))
        self.stop_loss = invalidation_price(cells.get("Trailing Stop", ""))
        if self.stop_loss is None and self.buy_limit is not None and self.trailing_stop_amount is not None:
            self.stop_loss = self.buy_limit - self.trailing_stop_amount
        self.take_profit = first_money(cells.get("Take Profit", ""))
        self.supports = money_values(cells.get("Key Support", ""))
        self.resistances = money_values(cells.get("Key Resistance", ""))
        self.sma_windows = mentioned_smas(raw)
        self.sma_windows.add(150)

    def _ticker(self) -> str:
        value = self.cells.get("Ticker", "").strip().upper()
        if value:
            return value
        match = re.search(r"\b[A-Z][A-Z0-9.-]{0,9}\b", self.raw)
        if match:
            return match.group(0)
        raise ValueError("Could not find ticker in setup line")


def main() -> int:
    args = parse_args()
    setup_text = args.setup_line if args.setup_line else sys.stdin.read()
    setup = parse_setup(setup_text)
    rows = load_feature_rows(setup.ticker, args.data_root)
    rows = filter_rows(rows, args.end_date)
    if not rows:
        raise SystemExit(f"No local daily feature rows found for {setup.ticker}")

    visible = rows[-args.days :]
    if len(visible) < 30:
        raise SystemExit(f"Only {len(visible)} feature rows found for {setup.ticker}; need at least 30")

    svg = render_svg(setup, visible, args.days)
    output = args.output or default_output_path(setup.ticker)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(svg, encoding="utf-8")
    print(output)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Render one Markdown table row from rankers/lower-risk-swing-entry.md "
            "as an SVG setup chart."
        )
    )
    parser.add_argument("--setup-line", help="One lower-risk-swing-entry table row. Defaults to stdin.")
    parser.add_argument("--output", type=Path, help="SVG output path.")
    parser.add_argument(
        "--days",
        type=int,
        default=DEFAULT_DAYS,
        help=f"Visible daily bars to render. Default: {DEFAULT_DAYS}.",
    )
    parser.add_argument("--end-date", help="Last chart date, YYYY-MM-DD. Defaults to latest local row.")
    parser.add_argument(
        "--data-root",
        type=Path,
        default=FEATURE_ROOT,
        help="Daily feature dataset root. Defaults to data/stock/features/daily.",
    )
    return parser.parse_args()


def parse_setup(text: str) -> Setup:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    table_lines = [
        line
        for line in lines
        if "|" in line and not re.match(r"^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?$", line)
    ]
    data_rows = [line for line in table_lines if "Ticker" not in split_markdown_row(line)]
    if data_rows:
        cells = split_markdown_row(data_rows[0])
        if len(cells) >= len(KNOWN_COLUMNS):
            return Setup(dict(zip(KNOWN_COLUMNS, cells[: len(KNOWN_COLUMNS)])), data_rows[0])

    raw = " ".join(lines)
    fallback = {
        "Ticker": "",
        "Current Price": "",
        "Key Support": section_after(raw, "support"),
        "Key Resistance": section_after(raw, "resistance"),
        "Buy Limit Order": section_after(raw, "buy"),
        "Trailing Stop": section_after(raw, "stop"),
        "Take Profit": section_after(raw, "profit"),
    }
    return Setup(fallback, raw)


def split_markdown_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def section_after(text: str, word: str) -> str:
    match = re.search(rf"\b{word}\b[^|;.]*", text, re.I)
    return match.group(0) if match else text


def money_values(text: str) -> list[float]:
    values = []
    for match in re.finditer(r"\$?\s*([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)", text):
        prefix = text[max(0, match.start() - 12) : match.start()].lower()
        suffix = text[match.end() : match.end() + 12].lower()
        if (
            "%" in suffix
            or "x" in suffix
            or "rank" in prefix
            or "sma" in prefix
            or "ema" in prefix
            or "day" in suffix
        ):
            continue
        values.append(float(match.group(1).replace(",", "")))
    return values


def first_money(text: str) -> float | None:
    values = money_values(text)
    return values[0] if values else None


def invalidation_price(text: str) -> float | None:
    patterns = [
        r"(?:invalidation|invalidates?)\D{0,30}(?:below|under)\D{0,10}\$?\s*([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)",
        r"(?:below|under)\D{0,10}\$?\s*([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)",
        r"(?:stop(?: loss)? at)\D{0,10}\$?\s*([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return float(match.group(1).replace(",", ""))
    return None


def mentioned_smas(text: str) -> set[int]:
    windows = set()
    for match in re.finditer(r"\b(?:SMA\s*|)(20|50|100|150|200)(?:[- ]?day)?\s*SMA\b", text, re.I):
        windows.add(int(match.group(1)))
    for match in re.finditer(r"\bSMA\s*(20|50|100|150|200)\b", text, re.I):
        windows.add(int(match.group(1)))
    return windows


def load_feature_rows(ticker: str, data_root: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in feature_paths(ticker, data_root):
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                if row.get("adj_close"):
                    rows.append(row)
    rows.sort(key=lambda row: row["date"])
    return rows


def feature_paths(ticker: str, data_root: Path) -> list[Path]:
    candidates = [ticker.upper(), ticker.upper().replace(".", "-"), ticker.upper().replace("-", ".")]
    paths: list[Path] = []
    for year_dir in sorted(path for path in data_root.iterdir() if path.is_dir()):
        for symbol in candidates:
            path = year_dir / f"{symbol}.csv"
            if path.exists():
                paths.append(path)
                break
    if not paths:
        checked = ", ".join(f"{symbol}.csv" for symbol in candidates)
        raise SystemExit(f"No local daily feature files found for {ticker}; checked {checked}")
    return paths


def filter_rows(rows: list[dict[str, str]], end_date: str | None) -> list[dict[str, str]]:
    if not end_date:
        return rows
    end = dt.date.fromisoformat(end_date)
    return [row for row in rows if dt.date.fromisoformat(row["date"]) <= end]


def default_output_path(ticker: str) -> Path:
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    return DEFAULT_OUTPUT_ROOT / f"{ticker.upper()}-{stamp}.svg"


def render_svg(setup: Setup, rows: list[dict[str, str]], requested_days: int) -> str:
    width = 1280
    height = 760
    margin_left = 82
    margin_right = 214
    margin_top = 76
    margin_bottom = 86
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom
    xs = [margin_left + i * plot_w / max(1, len(rows) - 1) for i in range(len(rows))]

    sma_windows = sorted(window for window in setup.sma_windows if window in SMA_COLUMNS)
    price_values = values_for(rows, "adj_close")
    y_values = []
    y_values.extend(values_for(rows, "adj_high"))
    y_values.extend(values_for(rows, "adj_low"))
    for window in sma_windows:
        y_values.extend(values_for(rows, SMA_COLUMNS[window]))
    y_values.extend(level_values(setup))
    y_min, y_max = padded_range(y_values)

    def y(value: float) -> float:
        return margin_top + (y_max - value) * plot_h / (y_max - y_min)

    def x(index: int) -> float:
        return xs[index]

    latest = rows[-1]
    title = f"{setup.ticker} lower-risk swing setup"
    subtitle = (
        f"{rows[0]['date']} to {rows[-1]['date']} | daily bars | "
        f"{len(rows)} of requested {requested_days} rows"
    )

    parts = [
        svg_header(width, height),
        rect(0, 0, width, height, "#f8fafc"),
        text(32, 34, title, 24, "#111827", weight="700"),
        text(32, 58, subtitle, 13, "#4b5563"),
        rect(margin_left, margin_top, plot_w, plot_h, "#ffffff", "#d1d5db"),
    ]
    parts.extend(grid_lines(margin_left, margin_top, plot_w, plot_h, y_min, y_max, y))

    entry_zone = compute_entry_zone(setup)
    if entry_zone:
        low, high = entry_zone
        parts.append(
            rect(
                margin_left,
                y(high),
                plot_w,
                max(2, y(low) - y(high)),
                "#86efac",
                opacity=0.22,
            )
        )
        parts.append(label_at_right(margin_left + plot_w, y((low + high) / 2), "entry zone", "#15803d"))

    line_specs = []
    for value in setup.supports:
        line_specs.append((value, "support", "#0891b2", "4 4"))
    for value in setup.resistances:
        line_specs.append((value, "resistance", "#c2410c", "4 4"))
    if setup.buy_limit is not None:
        line_specs.append((setup.buy_limit, "buy limit", "#16a34a", ""))
    if setup.stop_loss is not None:
        line_specs.append((setup.stop_loss, "stop loss", "#dc2626", ""))
    if setup.take_profit is not None:
        line_specs.append((setup.take_profit, "take profit", "#059669", ""))

    for value, label, color, dash in line_specs:
        parts.append(horizontal_line(margin_left, margin_left + plot_w, y(value), color, dash))
        parts.append(label_at_right(margin_left + plot_w, y(value), f"{label} ${value:.2f}", color))

    sma_colors = {20: "#2563eb", 50: "#7c3aed", 100: "#64748b", 150: "#9333ea", 200: "#0f766e"}
    for window in sma_windows:
        col = SMA_COLUMNS[window]
        parts.append(path_line(rows, col, x, y, sma_colors[window], width=2.0))
        latest_sma = last_float(rows, col)
        if latest_sma is not None:
            parts.append(label_at_right(margin_left + plot_w, y(latest_sma), f"SMA{window} ${latest_sma:.2f}", sma_colors[window]))

    parts.append(path_line(rows, "adj_close", x, y, "#111827", width=2.6))
    latest_close = to_float(latest.get("adj_close"))
    if latest_close is not None:
        parts.append(circle(x(len(rows) - 1), y(latest_close), 4.5, "#111827"))
        parts.append(label_at_right(margin_left + plot_w, y(latest_close), f"close ${latest_close:.2f}", "#111827"))

    parts.extend(axis_labels(rows, margin_left, margin_top, plot_w, plot_h, y_min, y_max))
    parts.extend(summary_box(setup, latest, width, margin_top))
    parts.append("</svg>\n")
    return "\n".join(parts)


def values_for(rows: Iterable[dict[str, str]], column: str) -> list[float]:
    values = []
    for row in rows:
        value = to_float(row.get(column))
        if value is not None:
            values.append(value)
    return values


def level_values(setup: Setup) -> list[float]:
    values = []
    values.extend(setup.supports)
    values.extend(setup.resistances)
    for value in [setup.current_price, setup.buy_limit, setup.stop_loss, setup.take_profit]:
        if value is not None and math.isfinite(value):
            values.append(value)
    return values


def padded_range(values: list[float]) -> tuple[float, float]:
    finite = [value for value in values if math.isfinite(value)]
    if not finite:
        return 0.0, 1.0
    low = min(finite)
    high = max(finite)
    if low == high:
        low *= 0.95
        high *= 1.05
    pad = (high - low) * 0.08
    return low - pad, high + pad


def to_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        parsed = float(value)
    except ValueError:
        return None
    return parsed if math.isfinite(parsed) else None


def last_float(rows: list[dict[str, str]], column: str) -> float | None:
    for row in reversed(rows):
        value = to_float(row.get(column))
        if value is not None:
            return value
    return None


def compute_entry_zone(setup: Setup) -> tuple[float, float] | None:
    if len(setup.buy_prices) >= 2:
        return min(setup.buy_prices), max(setup.buy_prices)
    if setup.buy_limit is None:
        return None
    if setup.supports:
        nearest_support = min(setup.supports, key=lambda value: abs(value - setup.buy_limit))
        low = min(nearest_support, setup.buy_limit)
        high = max(nearest_support, setup.buy_limit)
    else:
        low = setup.buy_limit * 0.99
        high = setup.buy_limit * 1.01
    if high - low < setup.buy_limit * 0.01:
        center = (high + low) / 2
        low = center - setup.buy_limit * 0.005
        high = center + setup.buy_limit * 0.005
    return low, high


def svg_header(width: int, height: int) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img">'
    )


def rect(
    x: float,
    y: float,
    width: float,
    height: float,
    fill: str,
    stroke: str | None = None,
    opacity: float | None = None,
) -> str:
    attrs = [f'x="{x:.2f}"', f'y="{y:.2f}"', f'width="{width:.2f}"', f'height="{height:.2f}"', f'fill="{fill}"']
    if stroke:
        attrs.append(f'stroke="{stroke}"')
    if opacity is not None:
        attrs.append(f'opacity="{opacity:.3f}"')
    return f"<rect {' '.join(attrs)} />"


def text(x: float, y: float, value: str, size: int, color: str, weight: str = "400", anchor: str = "start") -> str:
    return (
        f'<text x="{x:.2f}" y="{y:.2f}" font-family="Inter, Arial, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" fill="{color}" text-anchor="{anchor}">'
        f"{html.escape(value)}</text>"
    )


def grid_lines(margin_left: int, margin_top: int, plot_w: int, plot_h: int, y_min: float, y_max: float, y_func) -> list[str]:
    parts = []
    for i in range(6):
        value = y_min + (y_max - y_min) * i / 5
        yy = y_func(value)
        parts.append(horizontal_line(margin_left, margin_left + plot_w, yy, "#e5e7eb", ""))
        parts.append(text(margin_left - 10, yy + 4, f"${value:.0f}", 12, "#6b7280", anchor="end"))
    return parts


def horizontal_line(x1: float, x2: float, y: float, color: str, dash: str) -> str:
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<line x1="{x1:.2f}" x2="{x2:.2f}" y1="{y:.2f}" y2="{y:.2f}" stroke="{color}" stroke-width="1.4"{dash_attr} />'


def label_at_right(x: float, y: float, label: str, color: str) -> str:
    return text(x + 9, y + 4, label, 12, color, weight="700")


def path_line(rows: list[dict[str, str]], column: str, x_func, y_func, color: str, width: float) -> str:
    segments = []
    current = []
    for index, row in enumerate(rows):
        value = to_float(row.get(column))
        if value is None:
            if current:
                segments.append(current)
                current = []
            continue
        current.append((x_func(index), y_func(value)))
    if current:
        segments.append(current)

    paths = []
    for segment in segments:
        if len(segment) < 2:
            continue
        d = " ".join(
            ("M" if index == 0 else "L") + f"{point[0]:.2f},{point[1]:.2f}"
            for index, point in enumerate(segment)
        )
        paths.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width:.1f}" stroke-linejoin="round" stroke-linecap="round" />')
    return "\n".join(paths)


def circle(cx: float, cy: float, r: float, fill: str) -> str:
    return f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" fill="{fill}" />'


def axis_labels(rows: list[dict[str, str]], margin_left: int, margin_top: int, plot_w: int, plot_h: int, y_min: float, y_max: float) -> list[str]:
    parts = []
    for fraction in [0.0, 0.25, 0.5, 0.75, 1.0]:
        index = min(len(rows) - 1, round((len(rows) - 1) * fraction))
        xx = margin_left + plot_w * fraction
        parts.append(text(xx, margin_top + plot_h + 26, rows[index]["date"], 12, "#6b7280", anchor="middle"))
        parts.append(f'<line x1="{xx:.2f}" x2="{xx:.2f}" y1="{margin_top:.2f}" y2="{margin_top + plot_h:.2f}" stroke="#f3f4f6" />')
    return parts


def summary_box(setup: Setup, latest: dict[str, str], width: int, y: int) -> list[str]:
    x = width - 198
    rows = [
        ("Status", setup.cells.get("Setup Status", "N/A")),
        ("Current", money_text(setup.current_price or to_float(latest.get("adj_close")))),
        ("Buy", money_text(setup.buy_limit)),
        ("Stop", money_text(setup.stop_loss)),
        ("Target", money_text(setup.take_profit)),
        ("R/R", setup.cells.get("Reward/Risk", "N/A")),
    ]
    parts = [rect(x - 8, y, 166, 154, "#ffffff", "#d1d5db")]
    parts.append(text(x, y + 24, "Setup", 14, "#111827", weight="700"))
    offset = 48
    for label, value in rows:
        parts.append(text(x, y + offset, label, 11, "#6b7280"))
        parts.append(text(x + 72, y + offset, str(value), 11, "#111827", weight="700"))
        offset += 19
    return parts


def money_text(value: float | None) -> str:
    return "N/A" if value is None else f"${value:.2f}"


if __name__ == "__main__":
    raise SystemExit(main())
