#!/usr/bin/env python3
"""Precompute daily technical and point-in-time fundamental features.

Parameters:
    ``--prices-dir`` selects canonical input, ``--features-dir`` selects output,
    and repeatable ``--symbol`` values restrict processing.
External sources:
    Local yearly canonical price and quarterly fundamental CSVs only; no
    network service is accessed.
Side effects:
    Creates feature year directories, replaces generated per-symbol CSVs, and
    writes the feature dataset ``.notes`` file.
Examples:
    Recompute features for the full local dataset::

        python3 scripts/stock-data-enrichment/precompute_daily_stock_features.py

    Recompute only selected symbols into a separate tree::

        python3 scripts/stock-data-enrichment/precompute_daily_stock_features.py --symbol AAPL --symbol MSFT --features-dir /tmp/features
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
from collections import defaultdict, deque
from pathlib import Path


DEFAULT_SMA_WINDOWS = (20, 50, 100, 150, 200)
DEFAULT_RETURN_WINDOWS = (21, 63, 126, 252)
DEFAULT_HIGH_WINDOWS = (252,)
DEFAULT_RELATIVE_VOLUME_WINDOW = 50
DEFAULT_HIGH_RELATIVE_VOLUME_THRESHOLD = 1.5
FUNDAMENTAL_FIELDS = (
    "is_eps_growing",
    "is_profit_margins_increasing",
    "is_revenue_rises",
    "is_debt_lowers",
    "is_institutional_accumalation_rising",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Precompute daily features into data/stock/features/daily/<year>/<symbol>.csv"
    )
    parser.add_argument(
        "--prices-dir",
        type=Path,
        default=Path("data/stock/prices/daily"),
        help="Input yearly price directory.",
    )
    parser.add_argument(
        "--features-dir",
        type=Path,
        default=Path("data/stock/features/daily"),
        help="Output yearly feature directory.",
    )
    parser.add_argument(
        "--fundamentals-dir",
        type=Path,
        default=Path("data/stock/fundamentals/quarterly"),
        help="Input yearly point-in-time fundamental directory.",
    )
    parser.add_argument(
        "--institutions-dir",
        type=Path,
        default=Path("data/stock/institutions/quarterly"),
        help="Input dated institutional-holdings snapshot directory.",
    )
    parser.add_argument(
        "--benchmark-symbol",
        default="SPY",
        help="Benchmark used by is_relative_strength_high (default: SPY).",
    )
    parser.add_argument(
        "--symbol",
        action="append",
        dest="symbols",
        help="Only process this symbol. Can be passed more than once.",
    )
    return parser.parse_args()


def read_symbol_rows(prices_dir: Path) -> dict[str, list[dict[str, str]]]:
    rows_by_symbol: dict[str, list[dict[str, str]]] = defaultdict(list)
    for csv_path in sorted(prices_dir.glob("*/*.csv")):
        if csv_path.parent.name.startswith("."):
            continue
        with csv_path.open(newline="") as handle:
            for row in csv.DictReader(handle):
                symbol = row.get("symbol") or csv_path.stem
                if not row.get("date"):
                    continue
                rows_by_symbol[symbol].append(row)

    for rows in rows_by_symbol.values():
        rows.sort(key=lambda row: row["date"])
    return rows_by_symbol


def as_float(row: dict[str, str], column: str) -> float | None:
    value = row.get(column)
    if value in (None, ""):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def read_fundamental_rows(
    fundamentals_dir: Path,
) -> dict[str, list[dict[str, str]]]:
    """Read facts ordered by the first date on which they were observable."""
    rows_by_symbol: dict[str, list[dict[str, str]]] = defaultdict(list)
    for csv_path in sorted(fundamentals_dir.glob("*/*.csv")):
        with csv_path.open(newline="") as handle:
            for row in csv.DictReader(handle):
                symbol = row.get("symbol") or csv_path.stem
                if not row.get("available_date") or not row.get("fiscal_period_end"):
                    continue
                rows_by_symbol[symbol].append(row)
    for rows in rows_by_symbol.values():
        rows.sort(key=lambda row: (row["available_date"], row["fiscal_period_end"]))
    return rows_by_symbol


def read_institutional_rows(
    institutions_dir: Path,
) -> dict[str, list[dict[str, str]]]:
    rows_by_symbol: dict[str, list[dict[str, str]]] = defaultdict(list)
    for csv_path in sorted(institutions_dir.glob("*/*.csv")):
        with csv_path.open(newline="") as handle:
            for row in csv.DictReader(handle):
                symbol = row.get("symbol") or csv_path.stem
                if row.get("available_date"):
                    rows_by_symbol[symbol].append(row)
    for rows in rows_by_symbol.values():
        rows.sort(key=lambda row: row["available_date"])
    return rows_by_symbol


def bool_text(value: bool | None) -> str:
    return "" if value is None else ("true" if value else "false")


def fundamental_flags(rows: list[dict[str, str]]) -> dict[str, str]:
    """Compare the latest reported quarter with its year-ago quarter."""
    by_period: dict[str, dict[str, str]] = {}
    for row in rows:
        period = by_period.setdefault(row["fiscal_period_end"], {})
        for key, value in row.items():
            if value not in (None, ""):
                period[key] = value
    periods = [by_period[key] for key in sorted(by_period)]
    latest = periods[-1] if periods else None
    year_ago = None
    if latest:
        latest_end = dt.date.fromisoformat(latest["fiscal_period_end"])
        candidates = []
        for row in periods[:-1]:
            difference = (latest_end - dt.date.fromisoformat(row["fiscal_period_end"])).days
            if 300 <= difference <= 430:
                candidates.append((abs(difference - 365), row))
        if candidates:
            year_ago = min(candidates, key=lambda item: item[0])[1]

    latest_eps = as_float(latest, "diluted_eps") if latest else None
    prior_eps = as_float(year_ago, "diluted_eps") if year_ago else None
    latest_revenue = as_float(latest, "revenue") if latest else None
    prior_revenue = as_float(year_ago, "revenue") if year_ago else None
    latest_income = as_float(latest, "net_income") if latest else None
    prior_income = as_float(year_ago, "net_income") if year_ago else None
    latest_margin = (
        latest_income / latest_revenue
        if latest_income is not None and latest_revenue not in (None, 0)
        else None
    )
    prior_margin = (
        prior_income / prior_revenue
        if prior_income is not None and prior_revenue not in (None, 0)
        else None
    )
    latest_debt = as_float(latest, "total_debt") if latest else None
    year_ago_debt = as_float(year_ago, "total_debt") if year_ago else None
    latest_institutional = (
        as_float(periods[-1], "institutional_ownership_pct") if periods else None
    )
    prior_institutional = (
        as_float(periods[-2], "institutional_ownership_pct")
        if len(periods) >= 2
        else None
    )

    def greater(current: float | None, previous: float | None) -> bool | None:
        return None if current is None or previous is None else current > previous

    def lower(current: float | None, previous: float | None) -> bool | None:
        return None if current is None or previous is None else current < previous

    return {
        "is_eps_growing": bool_text(greater(latest_eps, prior_eps)),
        "is_profit_margins_increasing": bool_text(greater(latest_margin, prior_margin)),
        "is_revenue_rises": bool_text(greater(latest_revenue, prior_revenue)),
        "is_debt_lowers": bool_text(lower(latest_debt, year_ago_debt)),
        "is_institutional_accumalation_rising": bool_text(
            greater(latest_institutional, prior_institutional)
        ),
    }


def fmt(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.10f}".rstrip("0").rstrip(".")


class RollingHigh:
    def __init__(self, window: int) -> None:
        self.window = window
        self.values: deque[tuple[int, float]] = deque()

    def push(self, index: int, value: float) -> None:
        while self.values and self.values[-1][1] <= value:
            self.values.pop()
        self.values.append((index, value))
        min_index = index - self.window + 1
        while self.values and self.values[0][0] < min_index:
            self.values.popleft()

    def current(self, index: int) -> float | None:
        if index + 1 < self.window or not self.values:
            return None
        return self.values[0][1]


def feature_rows(
    rows: list[dict[str, str]],
    fundamental_rows: list[dict[str, str]] | None = None,
    benchmark_returns: dict[str, float] | None = None,
    institutional_rows: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    sums = {window: 0.0 for window in DEFAULT_SMA_WINDOWS}
    queues = {window: deque() for window in DEFAULT_SMA_WINDOWS}
    rolling_highs = {window: RollingHigh(window) for window in DEFAULT_HIGH_WINDOWS}
    adj_closes: list[float] = []
    volumes: deque[float] = deque()
    volume_sum = 0.0
    output: list[dict[str, str]] = []
    facts = fundamental_rows or []
    visible_facts: list[dict[str, str]] = []
    fact_index = 0
    current_fundamental_flags = {field: "" for field in FUNDAMENTAL_FIELDS}
    institutions = institutional_rows or []
    institution_index = 0
    institutional_accumulation = ""

    for index, row in enumerate(rows):
        close = as_float(row, "close")
        adj_close = as_float(row, "adj_close")
        open_price = as_float(row, "open")
        high = as_float(row, "high")
        low = as_float(row, "low")
        volume = as_float(row, "volume")

        if close is None or adj_close is None:
            continue

        adj_factor = adj_close / close if close else 1.0
        adj_open = open_price * adj_factor if open_price is not None else None
        adj_high = high * adj_factor if high is not None else None
        adj_low = low * adj_factor if low is not None else None

        adj_closes.append(adj_close)
        prior_average_volume = (
            volume_sum / DEFAULT_RELATIVE_VOLUME_WINDOW
            if len(volumes) == DEFAULT_RELATIVE_VOLUME_WINDOW
            else None
        )
        for window in DEFAULT_SMA_WINDOWS:
            queues[window].append(adj_close)
            sums[window] += adj_close
            if len(queues[window]) > window:
                sums[window] -= queues[window].popleft()

        for high_window in rolling_highs.values():
            high_window.push(index, adj_close)

        feature = {
            "symbol": row.get("symbol", ""),
            "date": row["date"],
            "bar_size": row.get("bar_size", ""),
            "open": row.get("open", ""),
            "high": row.get("high", ""),
            "low": row.get("low", ""),
            "close": row.get("close", ""),
            "adj_close": row.get("adj_close", ""),
            "volume": row.get("volume", ""),
            "adj_factor": fmt(adj_factor),
            "adj_open": fmt(adj_open),
            "adj_high": fmt(adj_high),
            "adj_low": fmt(adj_low),
        }

        for window in DEFAULT_SMA_WINDOWS:
            feature[f"sma_{window}"] = (
                fmt(sums[window] / window) if len(queues[window]) == window else ""
            )

        for window in DEFAULT_RETURN_WINDOWS:
            previous_index = len(adj_closes) - window - 1
            previous = adj_closes[previous_index] if previous_index >= 0 else None
            feature[f"ret_{window}"] = (
                fmt(adj_close / previous - 1.0) if previous else ""
            )

        for window, high_window in rolling_highs.items():
            rolling_high = high_window.current(index)
            feature[f"high_{window}"] = fmt(rolling_high)
            feature[f"dd_{window}"] = (
                fmt(adj_close / rolling_high - 1.0) if rolling_high else ""
            )

        facts_changed = False
        while fact_index < len(facts) and facts[fact_index]["available_date"] <= row["date"]:
            visible_facts.append(facts[fact_index])
            fact_index += 1
            facts_changed = True
        if facts_changed:
            current_fundamental_flags = fundamental_flags(visible_facts)
        feature.update(current_fundamental_flags)
        while (
            institution_index < len(institutions)
            and institutions[institution_index]["available_date"] <= row["date"]
        ):
            net_change = as_float(
                institutions[institution_index], "net_reported_shares_change"
            )
            institutional_accumulation = bool_text(
                None if net_change is None else net_change > 0
            )
            institution_index += 1
        feature["is_institutional_accumalation_rising"] = institutional_accumulation
        sma_200 = as_float(feature, "sma_200")
        feature["is_above_moving_average"] = bool_text(
            None if sma_200 is None else adj_close > sma_200
        )
        benchmark_return = (benchmark_returns or {}).get(row["date"])
        stock_return = as_float(feature, "ret_252")
        feature["is_relative_strength_high"] = bool_text(
            None
            if stock_return is None or benchmark_return is None
            else stock_return > benchmark_return
        )
        previous_close = adj_closes[-2] if len(adj_closes) >= 2 else None
        relative_volume = (
            volume / prior_average_volume
            if volume is not None and prior_average_volume not in (None, 0)
            else None
        )
        feature["relative_volume_50"] = fmt(relative_volume)
        feature["is_high_relative_volume"] = bool_text(
            None
            if relative_volume is None or previous_close is None
            else (
                adj_close > previous_close
                and relative_volume >= DEFAULT_HIGH_RELATIVE_VOLUME_THRESHOLD
            )
        )

        output.append(feature)
        if volume is not None:
            volumes.append(volume)
            volume_sum += volume
            if len(volumes) > DEFAULT_RELATIVE_VOLUME_WINDOW:
                volume_sum -= volumes.popleft()

    return output


def write_feature_rows(features_dir: Path, symbol: str, rows: list[dict[str, str]]) -> None:
    if not rows:
        return

    fieldnames = list(rows[0].keys())
    rows_by_year: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        rows_by_year[row["date"][:4]].append(row)

    for year, year_rows in sorted(rows_by_year.items()):
        year_dir = features_dir / year
        year_dir.mkdir(parents=True, exist_ok=True)
        path = year_dir / f"{symbol}.csv"
        with path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(year_rows)


def write_notes(features_dir: Path) -> None:
    features_dir.mkdir(parents=True, exist_ok=True)
    (features_dir / ".notes").write_text(
        "\n".join(
            [
                "# Daily stock feature dataset notes",
                "",
                "Dataset location: data/stock/features/daily/<year>/<symbol>.csv",
                "",
                "Derived from canonical prices in data/stock/prices/daily/<year>/<symbol>.csv.",
                "Rows are computed per symbol across all available years, then split by calendar year.",
                "Rolling values use adjusted close and require a full actual-trading-row window.",
                "",
                "Added columns:",
                "- adj_factor = adj_close / close",
                "- adj_open, adj_high, adj_low",
                "- sma_20, sma_50, sma_100, sma_150, sma_200",
                "- ret_21, ret_63, ret_126, ret_252",
                "- high_252, dd_252",
                "- is_eps_growing = latest reported quarterly diluted EPS > comparable year-ago quarter",
                "- is_profit_margins_increasing = latest reported quarterly net margin > comparable year-ago quarter",
                "- is_revenue_rises = latest reported quarterly revenue > comparable year-ago quarter",
                "- is_debt_lowers = latest reported total debt < comparable year-ago quarter",
                "- is_institutional_accumalation_rising = aggregate net reported institutional share change > 0",
                "- is_above_moving_average = adjusted close > SMA 200",
                "- is_relative_strength_high = 252-row return > SPY 252-row return",
                "- relative_volume_50 = current volume / mean volume of the prior 50 valid rows",
                "- is_high_relative_volume = up close with relative_volume_50 >= 1.5",
                "",
                "Institutional accumulation uses the latest Nasdaq snapshot's aggregate net reported share change.",
                "Fundamental facts and institutional snapshots are joined only from available_date onward; unavailable evidence stays blank.",
                "Blank OHLCV rows from the canonical data are skipped rather than forward-filled.",
                "",
            ]
        )
    )


def main() -> int:
    args = parse_args()
    rows_by_symbol = read_symbol_rows(args.prices_dir)
    fundamentals_by_symbol = read_fundamental_rows(args.fundamentals_dir)
    institutions_by_symbol = read_institutional_rows(args.institutions_dir)
    requested = set(args.symbols or rows_by_symbol.keys())
    benchmark_rows = rows_by_symbol.get(args.benchmark_symbol, [])
    benchmark_features = feature_rows(benchmark_rows)
    benchmark_returns = {
        row["date"]: value
        for row in benchmark_features
        for value in [as_float(row, "ret_252")]
        if value is not None
    }
    processed = 0
    written_rows = 0

    for symbol in sorted(requested):
        rows = rows_by_symbol.get(symbol)
        if not rows:
            print(f"skip {symbol}: no rows")
            continue
        features = feature_rows(
            rows,
            fundamentals_by_symbol.get(symbol),
            benchmark_returns,
            institutions_by_symbol.get(symbol),
        )
        write_feature_rows(args.features_dir, symbol, features)
        processed += 1
        written_rows += len(features)
        print(f"processed {symbol}: rows={len(features)}")

    write_notes(args.features_dir)
    print(f"done: symbols={processed} rows={written_rows} output={args.features_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
