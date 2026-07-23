#!/usr/bin/env python3
"""Run the fundamental-technical selector against dated forward outcomes."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
FEATURE_ROOT = ROOT / "data/stock/features/daily"
MODEL_PATH = ROOT / "stages/selection-models/fundamental_technical_momentum.py"
OUTPUT_ROOT = (
    ROOT / "artifacts/stock/backtests/components/selection-models/"
    "fundamental-technical-momentum"
)
HORIZONS = (21, 63, 126, 252, 378)
TARGET_COUNTS = (1, 5, 10, 20)
WINDOWS = (
    ("development-2021-2022", "2021-07-06", "2022-12-30"),
    ("development-2023-2024h1", "2023-01-03", "2024-06-28"),
    ("development-2024h2-2025m1", "2024-07-01", "2025-01-31"),
)
FUNDAMENTAL = (
    "is_eps_growing",
    "is_profit_margins_increasing",
    "is_revenue_rises",
    "is_debt_lowers",
)
TECHNICAL = (
    "is_institutional_accumalation_rising",
    "is_high_relative_volume",
    "is_above_moving_average",
    "is_relative_strength_high",
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)
    model = _module(MODEL_PATH)
    universes = {
        path.stem: _universe(path)
        for path in sorted((ROOT / "configuration/universes").glob("random-sp500-50-*.md"))
    }
    tickers = sorted({ticker for values in universes.values() for ticker in values} | {"SPY"})
    data_fingerprint = _data_fingerprint(tickers)
    tapes = {ticker: _rows(ticker) for ticker in tickers}
    config = {
        "model": "fundamental-technical-momentum",
        "universes": universes,
        "windows": WINDOWS,
        "frequency": "weekly",
        "horizons": HORIZONS,
        "target_counts": TARGET_COUNTS,
        "variants": tuple(_variants()),
        "entry": "next_valid_session_adjusted_open",
        "data_fingerprint": data_fingerprint,
    }
    digest = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()[:8]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%SZ")
    output = args.output_dir or OUTPUT_ROOT / f"{stamp}__exploratory-five-universes__{digest}"
    output.mkdir(parents=True, exist_ok=False)

    observations: list[dict[str, Any]] = []
    coverage: list[dict[str, Any]] = []
    outcome_cache: dict[tuple[str, str], dict[int, dict[str, float]]] = {}
    for universe_name, candidates in universes.items():
        for window_name, start, end in WINDOWS:
            cutoffs = _weekly_cutoffs(tapes["SPY"], start, end)
            prior_targets: dict[tuple[str, int], set[str]] = {}
            for cutoff in cutoffs:
                features = {
                    ticker: tapes[ticker]["by_date"].get(cutoff)
                    for ticker in candidates
                    if cutoff in tapes[ticker]["by_date"]
                }
                universe_returns = _universe_outcomes(
                    candidates, tapes, cutoff, outcome_cache
                )
                spy_returns = _cached_outcomes(tapes, "SPY", cutoff, outcome_cache)
                for variant, ignored in _variants().items():
                    adjusted = _variant_features(features, ignored)
                    for target_count in TARGET_COUNTS:
                        result = model.select(
                            as_of=cutoff,
                            candidates=candidates,
                            features=adjusted,
                            target_count=target_count,
                        )
                        eligible_count = len(result.ranking)
                        missing_count = sum(
                            any(reason.startswith("missing:") for reason in item["reasons"])
                            for item in result.eligibility.values()
                        )
                        key = (variant, target_count)
                        current = {target["instrument_id"] for target in result.targets}
                        previous = prior_targets.get(key)
                        turnover = (
                            None
                            if previous is None
                            else len(previous.symmetric_difference(current))
                            / max(1, len(previous) + len(current))
                        )
                        prior_targets[key] = current
                        coverage.append(
                            {
                                "universe": universe_name,
                                "window": window_name,
                                "cutoff": cutoff,
                                "variant": variant,
                                "target_count": target_count,
                                "candidate_count": len(candidates),
                                "feature_row_count": len(features),
                                "eligible_count": eligible_count,
                                "selected_count": len(result.targets),
                                "missing_evidence_count": missing_count,
                                "fallback_used": result.fallback_used,
                                "turnover": turnover,
                            }
                        )
                        for rank, target in enumerate(result.targets, 1):
                            ticker = target["instrument_id"]
                            outcomes = _cached_outcomes(
                                tapes, ticker, cutoff, outcome_cache
                            )
                            for horizon in HORIZONS:
                                outcome = outcomes.get(horizon)
                                if outcome is None:
                                    continue
                                observations.append(
                                    {
                                        "universe": universe_name,
                                        "window": window_name,
                                        "cutoff": cutoff,
                                        "variant": variant,
                                        "target_count": target_count,
                                        "rank": rank,
                                        "ticker": ticker,
                                        "horizon": horizon,
                                        "forward_return": outcome["return"],
                                        "max_adverse_excursion": outcome["mae"],
                                        "max_favorable_excursion": outcome["mfe"],
                                        "spy_return": spy_returns.get(horizon, {}).get("return"),
                                        "universe_return": universe_returns.get(horizon),
                                    }
                                )

    summaries = _summaries(observations, coverage)
    _write_csv(output / "run_config.csv", _flatten_config(config, digest))
    _write_csv(output / "coverage.csv", coverage)
    _write_csv(output / "outcomes.csv", observations)
    _write_csv(output / "summary.csv", summaries)
    _report(output, config, digest, summaries, coverage)
    print(output.relative_to(ROOT))
    return 0


def _variants() -> dict[str, set[str]]:
    variants = {
        "full": set(),
        "unfiltered": set(FUNDAMENTAL + TECHNICAL),
        "fundamental_only": set(TECHNICAL),
        "technical_demand_only": set(FUNDAMENTAL),
    }
    for field in FUNDAMENTAL + TECHNICAL:
        variants[f"leave_one_out:{field}"] = {field}
    return variants


def _variant_features(
    features: Mapping[str, Mapping[str, Any]], ignored: set[str]
) -> dict[str, dict[str, Any]]:
    result = {}
    for ticker, row in features.items():
        copy = dict(row)
        for field in ignored:
            copy[field] = "true"
        result[ticker] = copy
    return result


def _rows(ticker: str) -> dict[str, Any]:
    rows = []
    for path in sorted(FEATURE_ROOT.glob(f"*/{ticker}.csv")):
        with path.open(newline="", encoding="utf-8") as handle:
            rows.extend(csv.DictReader(handle))
    rows = [row for row in rows if row.get("date") and row.get("adj_close")]
    rows.sort(key=lambda row: row["date"])
    return {"rows": rows, "by_date": {row["date"]: row for row in rows}, "index": {
        row["date"]: index for index, row in enumerate(rows)
    }}


def _outcomes(tape: Mapping[str, Any], cutoff: str) -> dict[int, dict[str, float]]:
    index = tape["index"].get(cutoff)
    rows = tape["rows"]
    if index is None or index + 1 >= len(rows):
        return {}
    entry_index = index + 1
    entry = _number(rows[entry_index].get("adj_open"))
    if entry is None:
        return {}
    result = {}
    lowest = float("inf")
    highest = float("-inf")
    for offset, row in enumerate(rows[entry_index : entry_index + max(HORIZONS)], 1):
        close = _number(row.get("adj_close"))
        low = _number(row.get("adj_low"))
        high = _number(row.get("adj_high"))
        if close is None or low is None or high is None:
            break
        lowest = min(lowest, low)
        highest = max(highest, high)
        if offset in HORIZONS:
            result[offset] = {
                "return": close / entry - 1.0,
                "mae": lowest / entry - 1.0,
                "mfe": highest / entry - 1.0,
            }
    return result


def _cached_outcomes(
    tapes: Mapping[str, Mapping[str, Any]],
    ticker: str,
    cutoff: str,
    cache: dict[tuple[str, str], dict[int, dict[str, float]]],
) -> dict[int, dict[str, float]]:
    key = (ticker, cutoff)
    if key not in cache:
        cache[key] = _outcomes(tapes[ticker], cutoff)
    return cache[key]


def _universe_outcomes(
    candidates: Sequence[str],
    tapes: Mapping[str, Mapping[str, Any]],
    cutoff: str,
    cache: dict[tuple[str, str], dict[int, dict[str, float]]],
) -> dict[int, float]:
    values: dict[int, list[float]] = defaultdict(list)
    for ticker in candidates:
        for horizon, outcome in _cached_outcomes(tapes, ticker, cutoff, cache).items():
            values[horizon].append(outcome["return"])
    return {horizon: statistics.mean(returns) for horizon, returns in values.items()}


def _weekly_cutoffs(tape: Mapping[str, Any], start: str, end: str) -> list[str]:
    weeks: dict[tuple[int, int], str] = {}
    for row in tape["rows"]:
        date = row["date"]
        if start <= date <= end:
            parsed = datetime.strptime(date, "%Y-%m-%d").date()
            iso = parsed.isocalendar()
            weeks[(iso[0], iso[1])] = date
    return list(weeks.values())


def _summaries(
    observations: Sequence[Mapping[str, Any]], coverage: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], list[Mapping[str, Any]]] = defaultdict(list)
    for row in observations:
        key = (row["universe"], row["window"], row["variant"], row["target_count"], row["horizon"])
        grouped[key].append(row)
    coverage_grouped: dict[tuple[Any, ...], list[Mapping[str, Any]]] = defaultdict(list)
    for row in coverage:
        coverage_grouped[(row["universe"], row["window"], row["variant"], row["target_count"])].append(row)
    summaries = []
    dimensions = {
        (row["universe"], row["window"], row["variant"], row["target_count"])
        for row in coverage
    }
    for base in sorted(dimensions):
        cov = coverage_grouped[base]
        for horizon in HORIZONS:
            rows = grouped.get(base + (horizon,), [])
            returns = [row["forward_return"] for row in rows]
            spy = [row["forward_return"] - row["spy_return"] for row in rows if row["spy_return"] is not None]
            universe = [
                row["forward_return"] - row["universe_return"]
                for row in rows if row["universe_return"] is not None
            ]
            summaries.append(
                {
                    "universe": base[0],
                    "window": base[1],
                    "variant": base[2],
                    "target_count": base[3],
                    "horizon": horizon,
                    "decision_count": len(cov),
                    "observation_count": len(rows),
                    "eligible_coverage": _mean([row["eligible_count"] / row["candidate_count"] for row in cov]),
                    "selection_rate": _mean([row["selected_count"] > 0 for row in cov]),
                    "missing_evidence_rate": _mean([row["missing_evidence_count"] / row["candidate_count"] for row in cov]),
                    "mean_return": _mean(returns),
                    "median_return": statistics.median(returns) if returns else None,
                    "hit_rate": _mean([value > 0 for value in returns]),
                    "hit_rate_above_spy": _mean([value > 0 for value in spy]),
                    "mean_excess_spy": _mean(spy),
                    "mean_excess_universe": _mean(universe),
                    "mean_mae": _mean([row["max_adverse_excursion"] for row in rows]),
                    "mean_mfe": _mean([row["max_favorable_excursion"] for row in rows]),
                    "mean_turnover": _mean([row["turnover"] for row in cov if row["turnover"] is not None]),
                    "unique_tickers": len({row["ticker"] for row in rows}),
                }
            )
    return summaries


def _report(
    output: Path,
    config: Mapping[str, Any],
    digest: str,
    summaries: Sequence[Mapping[str, Any]],
    coverage: Sequence[Mapping[str, Any]],
) -> None:
    full = [row for row in summaries if row["variant"] == "full" and row["target_count"] == 10]
    technical = [
        row for row in summaries
        if row["variant"] == "technical_demand_only" and row["target_count"] == 10
    ]
    lines = [
        "# Execution Report", "",
        f"- Configuration hash: `{digest}`",
        f"- Universes: `{len(config['universes'])}` current-constituent random universes",
        f"- Windows: `{len(config['windows'])}` exploratory development windows",
        f"- Decision rows: `{len(coverage)}`", "",
        "## Data Quality", "",
        (
            "The full conjunction produced point-in-time eligible observations. "
            "Missing feature evidence was excluded and reported without being converted "
            "into passing or failing observations."
            if sum(row["observation_count"] for row in full) > 0
            else
            "The full conjunction produced no point-in-time eligible observations. "
            "Missing feature evidence was excluded and reported without being converted "
            "into passing or failing observations."
        ), "",
        "## Full Model", "",
        "| Horizon | Observations | Mean return | Excess vs SPY | Excess vs universe |",
        "| ---: | ---: | ---: | ---: | ---: |",
    ]
    for horizon in HORIZONS:
        rows = [row for row in full if row["horizon"] == horizon]
        lines.append(
            f"| {horizon} | {sum(row['observation_count'] for row in rows)} | "
            f"{_pct(_weighted(rows, 'mean_return'))} | {_pct(_weighted(rows, 'mean_excess_spy'))} | "
            f"{_pct(_weighted(rows, 'mean_excess_universe'))} |"
        )
    lines += ["", "## Technical/Demand Baseline (Target Count 10)", "",
              "| Horizon | Observations | Mean return | Excess vs SPY | Excess vs universe |",
              "| ---: | ---: | ---: | ---: | ---: |"]
    for horizon in HORIZONS:
        rows = [row for row in technical if row["horizon"] == horizon]
        lines.append(
            f"| {horizon} | {sum(row['observation_count'] for row in rows)} | "
            f"{_pct(_weighted(rows, 'mean_return'))} | {_pct(_weighted(rows, 'mean_excess_spy'))} | "
            f"{_pct(_weighted(rows, 'mean_excess_universe'))} |"
        )
    lines += ["", "## Interpretation", "",
              "This run is an exploratory component benchmark with current-universe bias. "
              "It is not a strategy backtest and not promotion evidence."]
    (output / "execution-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _weighted(rows: Sequence[Mapping[str, Any]], field: str) -> float | None:
    usable = [(row[field], row["observation_count"]) for row in rows if row[field] is not None]
    total = sum(weight for _, weight in usable)
    return sum(value * weight for value, weight in usable) / total if total else None


def _flatten_config(config: Mapping[str, Any], digest: str) -> list[dict[str, str]]:
    rows = [{"key": "config_hash", "value": digest}]
    for key, value in config.items():
        rows.append({"key": key, "value": json.dumps(value, sort_keys=True)})
    return rows


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _universe(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return [line[3:-1] for line in text.splitlines() if line.startswith("- `") and line.endswith("`")]


def _module(path: Path):
    spec = importlib.util.spec_from_file_location("fundamental_technical_momentum_benchmark_model", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _data_fingerprint(tickers: Sequence[str]) -> str:
    """Identify the exact canonical feature inputs used by this run."""
    digest = hashlib.sha256()
    ticker_set = set(tickers)
    paths = sorted(
        path for path in FEATURE_ROOT.glob("*/*.csv")
        if path.stem in ticker_set and "2020" <= path.parent.name <= "2026"
    )
    for path in paths:
        digest.update(str(path.relative_to(ROOT)).encode())
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
    return digest.hexdigest()


def _number(value: Any) -> float | None:
    try:
        return None if value in (None, "") else float(value)
    except (TypeError, ValueError):
        return None


def _mean(values: Iterable[Any]) -> float | None:
    values = list(values)
    return statistics.mean(values) if values else None


def _pct(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.2%}"


if __name__ == "__main__":
    raise SystemExit(main())
