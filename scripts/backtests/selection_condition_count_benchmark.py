#!/usr/bin/env python3
"""Benchmark forward outcomes by number of true selector conditions."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
BASE_PATH = ROOT / "scripts/backtests/selection_model_forward_outcome_benchmark.py"
MODEL_PATH = ROOT / "stages/selection-models/fundamental_technical_momentum.py"
OUTPUT_ROOT = (
    ROOT / "artifacts/stock/backtests/components/selection-models/"
    "fundamental-technical-condition-count"
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)
    base = load_module(BASE_PATH, "condition_count_base")
    model = load_module(MODEL_PATH, "condition_count_model")
    fields = tuple(model.BOOLEAN_FIELDS)
    universes = {
        path.stem: base._universe(path)
        for path in sorted((ROOT / "configuration/universes").glob("random-sp500-50-*.md"))
    }
    tickers = sorted({ticker for values in universes.values() for ticker in values} | {"SPY"})
    tapes = {ticker: base._rows(ticker) for ticker in tickers}
    config = {
        "diagnostic": "fundamental-technical-condition-count",
        "universes": universes,
        "windows": base.WINDOWS,
        "frequency": "weekly",
        "horizons": base.HORIZONS,
        "boolean_fields": fields,
        "missing_policy": "exclude_from_count_and_report",
        "aggregation": "equal_weight_within_dated_count_then_equal_weight_cells",
        "data_fingerprint": base._data_fingerprint(tickers),
    }
    config_hash = hashlib.sha256(
        json.dumps(config, sort_keys=True).encode()
    ).hexdigest()[:8]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%SZ")
    output = args.output_dir or OUTPUT_ROOT / (
        f"{stamp}__five-universes-three-windows__{config_hash}"
    )
    output.mkdir(parents=True, exist_ok=False)

    candidates: list[dict[str, Any]] = []
    raw_outcomes: list[dict[str, Any]] = []
    outcome_cache: dict[tuple[str, str], dict[int, dict[str, float]]] = {}
    for universe_name, universe in universes.items():
        for window_name, start, end in base.WINDOWS:
            for cutoff in base._weekly_cutoffs(tapes["SPY"], start, end):
                spy = base._cached_outcomes(tapes, "SPY", cutoff, outcome_cache)
                universe_outcomes = base._universe_outcomes(
                    universe, tapes, cutoff, outcome_cache
                )
                for ticker in universe:
                    row = tapes[ticker]["by_date"].get(cutoff)
                    values = {
                        field: boolean(row.get(field)) if row else None
                        for field in fields
                    }
                    missing = tuple(field for field, value in values.items() if value is None)
                    count = None if missing else sum(bool(value) for value in values.values())
                    signature = (
                        ""
                        if missing
                        else "|".join(field for field in fields if values[field]) or "none"
                    )
                    candidate = {
                        "universe": universe_name,
                        "window": window_name,
                        "cutoff": cutoff,
                        "ticker": ticker,
                        "complete_evidence": not missing,
                        "condition_count": "" if count is None else count,
                        "signature": signature,
                        "missing_fields": "|".join(missing),
                    }
                    candidates.append(candidate)
                    if count is None:
                        continue
                    outcomes = base._cached_outcomes(
                        tapes, ticker, cutoff, outcome_cache
                    )
                    for horizon in base.HORIZONS:
                        outcome = outcomes.get(horizon)
                        if outcome is None:
                            continue
                        raw_outcomes.append({
                            **candidate,
                            "horizon": horizon,
                            "forward_return": outcome["return"],
                            "max_adverse_excursion": outcome["mae"],
                            "max_favorable_excursion": outcome["mfe"],
                            "spy_return": spy.get(horizon, {}).get("return"),
                            "universe_return": universe_outcomes.get(horizon),
                        })

    cohort_rows = dated_cohorts(raw_outcomes)
    count_summary = summarize_counts(cohort_rows)
    signature_summary = summarize_signatures(raw_outcomes)
    monotonicity = summarize_monotonicity(count_summary)
    write_csv(output / "run_config.csv", flatten_config(config, config_hash))
    write_csv(output / "candidates.csv", candidates)
    write_csv(output / "outcomes.csv", raw_outcomes)
    write_csv(output / "dated_count_cohorts.csv", cohort_rows)
    write_csv(output / "count_summary.csv", count_summary)
    write_csv(output / "signature_summary.csv", signature_summary)
    write_csv(output / "monotonicity.csv", monotonicity)
    write_report(
        output, config_hash, candidates, raw_outcomes, count_summary, monotonicity
    )
    print(output.relative_to(ROOT))
    return 0


def dated_cohorts(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        key = (
            row["universe"], row["window"], row["cutoff"],
            int(row["condition_count"]), int(row["horizon"]),
        )
        grouped[key].append(row)
    result = []
    for key, values in sorted(grouped.items()):
        result.append({
            "universe": key[0],
            "window": key[1],
            "cutoff": key[2],
            "condition_count": key[3],
            "horizon": key[4],
            "ticker_count": len(values),
            "mean_return": mean(values, "forward_return"),
            "median_return": statistics.median(
                float(row["forward_return"]) for row in values
            ),
            "positive_rate": statistics.mean(
                float(row["forward_return"]) > 0 for row in values
            ),
            "mean_excess_spy": statistics.mean(
                float(row["forward_return"]) - float(row["spy_return"])
                for row in values if row["spy_return"] is not None
            ),
            "mean_excess_universe": statistics.mean(
                float(row["forward_return"]) - float(row["universe_return"])
                for row in values if row["universe_return"] is not None
            ),
            "mean_mae": mean(values, "max_adverse_excursion"),
            "mean_mfe": mean(values, "max_favorable_excursion"),
        })
    return result


def summarize_counts(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[int, int], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(int(row["condition_count"]), int(row["horizon"]))].append(row)
    result = []
    for (count, horizon), values in sorted(grouped.items()):
        result.append({
            "condition_count": count,
            "horizon": horizon,
            "dated_cohort_count": len(values),
            "security_observation_count": sum(int(row["ticker_count"]) for row in values),
            "mean_return": mean(values, "mean_return"),
            "median_cohort_return": statistics.median(
                float(row["mean_return"]) for row in values
            ),
            "positive_rate": mean(values, "positive_rate"),
            "mean_excess_spy": mean(values, "mean_excess_spy"),
            "mean_excess_universe": mean(values, "mean_excess_universe"),
            "mean_mae": mean(values, "mean_mae"),
            "mean_mfe": mean(values, "mean_mfe"),
        })
    return result


def summarize_signatures(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, int], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["signature"]), int(row["horizon"]))].append(row)
    result = []
    for (signature, horizon), values in sorted(grouped.items()):
        result.append({
            "signature": signature,
            "condition_count": int(values[0]["condition_count"]),
            "horizon": horizon,
            "observation_count": len(values),
            "dated_cell_count": len({
                (row["universe"], row["window"], row["cutoff"]) for row in values
            }),
            "unique_tickers": len({row["ticker"] for row in values}),
            "mean_return": mean(values, "forward_return"),
            "mean_excess_spy": statistics.mean(
                float(row["forward_return"]) - float(row["spy_return"])
                for row in values if row["spy_return"] is not None
            ),
            "mean_excess_universe": statistics.mean(
                float(row["forward_return"]) - float(row["universe_return"])
                for row in values if row["universe_return"] is not None
            ),
        })
    return result


def summarize_monotonicity(
    summaries: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    result = []
    horizons = sorted({int(row["horizon"]) for row in summaries})
    for horizon in horizons:
        rows = sorted(
            (row for row in summaries if int(row["horizon"]) == horizon),
            key=lambda row: int(row["condition_count"]),
        )
        counts = [int(row["condition_count"]) for row in rows]
        for metric in ("mean_return", "mean_excess_spy", "mean_excess_universe"):
            values = [float(row[metric]) for row in rows]
            increases = sum(right > left for left, right in zip(values, values[1:]))
            result.append({
                "horizon": horizon,
                "metric": metric,
                "populated_counts": "|".join(map(str, counts)),
                "adjacent_comparisons": max(0, len(values) - 1),
                "adjacent_increases": increases,
                "spearman": spearman(counts, values),
                "linear_slope_per_condition": linear_slope(counts, values),
            })
    return result


def write_report(
    output: Path,
    config_hash: str,
    candidates: Sequence[Mapping[str, Any]],
    outcomes: Sequence[Mapping[str, Any]],
    summaries: Sequence[Mapping[str, Any]],
    monotonicity: Sequence[Mapping[str, Any]],
) -> None:
    complete = sum(bool(row["complete_evidence"]) for row in candidates)
    lines = [
        "# Execution Report", "",
        f"- Configuration hash: `{config_hash}`",
        f"- Candidate-date rows: `{len(candidates)}`",
        f"- Complete-evidence rows: `{complete}` ({complete / len(candidates):.2%})",
        f"- Forward outcome rows: `{len(outcomes)}`", "",
        "## Count Cohorts", "",
        "| Count | Horizon | Security observations | Dated cohorts | Mean return | vs SPY | vs universe |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summaries:
        lines.append(
            f"| {row['condition_count']} | {row['horizon']} | "
            f"{row['security_observation_count']} | {row['dated_cohort_count']} | "
            f"{row['mean_return']:.2%} | {row['mean_excess_spy']:.2%} | "
            f"{row['mean_excess_universe']:.2%} |"
        )
    lines += ["", "## Monotonicity", "",
              "| Horizon | Metric | Adjacent increases | Spearman | Slope/condition |",
              "| ---: | --- | ---: | ---: | ---: |"]
    for row in monotonicity:
        lines.append(
            f"| {row['horizon']} | {row['metric']} | "
            f"{row['adjacent_increases']}/{row['adjacent_comparisons']} | "
            f"{row['spearman']:.3f} | {row['linear_slope_per_condition']:.2%} |"
        )
    lines += [
        "", "## Scope", "",
        "This is a complete-case selector diagnostic, not a production "
        "count-based selector or portfolio backtest. Missing evidence was not "
        "converted to false.",
    ]
    (output / "execution-report.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def boolean(value: Any) -> bool | None:
    if value is True or value == "true":
        return True
    if value is False or value == "false":
        return False
    return None


def mean(rows: Sequence[Mapping[str, Any]], field: str) -> float:
    return statistics.mean(float(row[field]) for row in rows)


def spearman(xs: Sequence[float], ys: Sequence[float]) -> float:
    if len(xs) < 2:
        return float("nan")
    rx = ranks(xs)
    ry = ranks(ys)
    mx, my = statistics.mean(rx), statistics.mean(ry)
    numerator = sum((x - mx) * (y - my) for x, y in zip(rx, ry))
    denominator = math.sqrt(
        sum((x - mx) ** 2 for x in rx) * sum((y - my) ** 2 for y in ry)
    )
    return numerator / denominator if denominator else float("nan")


def ranks(values: Sequence[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda index: values[index])
    result = [0.0] * len(values)
    index = 0
    while index < len(order):
        end = index
        while end + 1 < len(order) and values[order[end + 1]] == values[order[index]]:
            end += 1
        rank = (index + end) / 2.0 + 1.0
        for position in range(index, end + 1):
            result[order[position]] = rank
        index = end + 1
    return result


def linear_slope(xs: Sequence[float], ys: Sequence[float]) -> float:
    mx, my = statistics.mean(xs), statistics.mean(ys)
    denominator = sum((x - mx) ** 2 for x in xs)
    return (
        sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / denominator
        if denominator else float("nan")
    )


def flatten_config(config: Mapping[str, Any], digest: str) -> list[dict[str, str]]:
    return [{"key": "config_hash", "value": digest}] + [
        {"key": key, "value": json.dumps(value, sort_keys=True)}
        for key, value in config.items()
    ]


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    raise SystemExit(main())
