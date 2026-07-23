#!/usr/bin/env python3
"""Validate continuous fundamental-momentum ranking on a fresh window."""

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
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
BASE_PATH = ROOT / "scripts/backtests/selection_model_forward_outcome_benchmark.py"
CONTINUOUS_PATH = ROOT / "stages/selection-models/continuous_fundamental_momentum.py"
LEGACY_PATH = ROOT / "stages/selection-models/fundamental_technical_momentum.py"
OUTPUT_ROOT = ROOT / (
    "artifacts/stock/backtests/components/selection-models/"
    "continuous-fundamental-momentum-validation"
)
WINDOW = ("validation-2025h2", "2025-07-21", "2026-01-16")
HORIZONS = (21, 63, 126)
TARGET_COUNTS = (5, 10, 20)
VARIANTS = ("continuous_fundamental_momentum", "momentum_only", "seven_condition")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)
    base = load_module(BASE_PATH, "continuous_validation_base")
    continuous = load_module(CONTINUOUS_PATH, "continuous_validation_model")
    legacy = load_module(LEGACY_PATH, "continuous_validation_legacy")
    universes = {
        path.stem: base._universe(path)
        for path in sorted((ROOT / "configuration/universes").glob("random-sp500-50-*.md"))
    }
    tickers = sorted({ticker for values in universes.values() for ticker in values} | {"SPY"})
    tapes = {ticker: base._rows(ticker) for ticker in tickers}
    config = {
        "model": "continuous-fundamental-momentum",
        "window": WINDOW,
        "horizons": HORIZONS,
        "target_counts": TARGET_COUNTS,
        "variants": VARIANTS,
        "universes": universes,
        "score": {"momentum_weight": 0.5, "fundamental_weight": 0.5,
                  "minimum_known_fundamentals": 4},
        "data_fingerprint": base._data_fingerprint(tickers),
    }
    config_hash = hashlib.sha256(
        json.dumps(config, sort_keys=True).encode()
    ).hexdigest()[:8]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%SZ")
    output = args.output_dir or OUTPUT_ROOT / f"{stamp}__unused-2025h2__{config_hash}"
    output.mkdir(parents=True, exist_ok=False)
    coverage, outcomes = [], []
    cache: dict[tuple[str, str], dict[int, dict[str, float]]] = {}
    for universe_name, candidates in universes.items():
        for cutoff in base._weekly_cutoffs(tapes["SPY"], WINDOW[1], WINDOW[2]):
            features = {
                ticker: tapes[ticker]["by_date"].get(cutoff)
                for ticker in candidates if cutoff in tapes[ticker]["by_date"]
            }
            spy = base._cached_outcomes(tapes, "SPY", cutoff, cache)
            universe_returns = base._universe_outcomes(candidates, tapes, cutoff, cache)
            for variant in VARIANTS:
                for target_count in TARGET_COUNTS:
                    if variant == "continuous_fundamental_momentum":
                        result = continuous.select(
                            as_of=cutoff, candidates=candidates, features=features,
                            target_count=target_count,
                        )
                    elif variant == "seven_condition":
                        result = legacy.select_without_high_relative_volume(
                            as_of=cutoff, candidates=candidates, features=features,
                            target_count=target_count,
                        )
                    else:
                        ranked = [
                            item for item in sorted(
                                ((ticker, _number(row.get("ret_252")))
                                 for ticker, row in features.items()),
                                key=lambda item: (
                                    -(item[1] if item[1] is not None else float("-inf")),
                                    item[0],
                                ),
                            ) if item[1] is not None
                        ]
                        result = SimpleResult(ranked, target_count)
                    coverage.append({
                        "universe": universe_name, "window": WINDOW[0],
                        "cutoff": cutoff, "variant": variant,
                        "target_count": target_count,
                        "eligible_count": len(result.ranking),
                        "selected_count": len(result.targets),
                        "candidate_count": len(candidates),
                    })
                    for rank, target in enumerate(result.targets, 1):
                        ticker = target["instrument_id"]
                        measured = base._cached_outcomes(tapes, ticker, cutoff, cache)
                        for horizon in HORIZONS:
                            outcome = measured.get(horizon)
                            if outcome is None:
                                continue
                            outcomes.append({
                                "universe": universe_name, "window": WINDOW[0],
                                "cutoff": cutoff, "variant": variant,
                                "target_count": target_count, "rank": rank,
                                "ticker": ticker, "horizon": horizon,
                                "forward_return": outcome["return"],
                                "max_adverse_excursion": outcome["mae"],
                                "max_favorable_excursion": outcome["mfe"],
                                "spy_return": spy.get(horizon, {}).get("return"),
                                "universe_return": universe_returns.get(horizon),
                            })
    summaries = summarize(outcomes)
    paired = paired_comparisons(outcomes)
    write_csv(output / "run_config.csv", flatten(config, config_hash))
    write_csv(output / "coverage.csv", coverage)
    write_csv(output / "outcomes.csv", outcomes)
    write_csv(output / "summary.csv", summaries)
    write_csv(output / "paired_comparisons.csv", paired)
    write_report(output, config_hash, coverage, outcomes, summaries, paired)
    print(output.relative_to(ROOT))
    return 0


class SimpleResult:
    def __init__(self, ranking: Sequence[tuple[str, float]], target_count: int):
        self.ranking = tuple(
            {"instrument_id": ticker, "ret_252": value, "rank": index + 1}
            for index, (ticker, value) in enumerate(ranking)
        )
        selected = self.ranking[:target_count]
        weight = 1.0 / len(selected) if selected else 0.0
        self.targets = tuple(
            {"instrument_id": row["instrument_id"], "weight": weight}
            for row in selected
        )


def _number(value: Any) -> float | None:
    try:
        return None if value in (None, "") else float(value)
    except (TypeError, ValueError):
        return None


def summarize(outcomes: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, int, int], list[Mapping[str, Any]]] = defaultdict(list)
    for row in outcomes:
        grouped[(row["variant"], int(row["target_count"]), int(row["horizon"]))].append(row)
    result = []
    for key, rows in sorted(grouped.items()):
        returns = [float(row["forward_return"]) for row in rows]
        tickers = {row["ticker"] for row in rows}
        result.append({
            "variant": key[0], "target_count": key[1], "horizon": key[2],
            "observation_count": len(rows),
            "selection_decision_count": len({
                (row["universe"], row["cutoff"]) for row in rows
            }),
            "unique_tickers": len(tickers),
            "max_ticker_concentration": max(
                sum(row["ticker"] == ticker for row in rows) / len(rows)
                for ticker in tickers
            ),
            "mean_return": statistics.mean(returns),
            "median_return": statistics.median(returns),
            "positive_rate": statistics.mean(value > 0 for value in returns),
            "spy_beating_rate": statistics.mean(
                float(row["forward_return"]) > float(row["spy_return"])
                for row in rows if row["spy_return"] is not None
            ),
            "mean_excess_spy": statistics.mean(
                float(row["forward_return"]) - float(row["spy_return"])
                for row in rows if row["spy_return"] is not None
            ),
            "mean_excess_universe": statistics.mean(
                float(row["forward_return"]) - float(row["universe_return"])
                for row in rows if row["universe_return"] is not None
            ),
            "mean_mae": statistics.mean(float(row["max_adverse_excursion"]) for row in rows),
            "mean_mfe": statistics.mean(float(row["max_favorable_excursion"]) for row in rows),
        })
    return result


def paired_comparisons(outcomes: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, int, int, str, str], list[float]] = defaultdict(list)
    for row in outcomes:
        grouped[(row["variant"], int(row["target_count"]), int(row["horizon"]),
                 row["universe"], row["cutoff"])].append(float(row["forward_return"]))
    result = []
    universes = sorted({row["universe"] for row in outcomes})
    cutoffs = sorted({row["cutoff"] for row in outcomes})
    for target_count in TARGET_COUNTS:
        for horizon in HORIZONS:
            for universe in universes:
                differences = []
                for cutoff in cutoffs:
                    test = grouped.get(("continuous_fundamental_momentum", target_count,
                                        horizon, universe, cutoff))
                    baseline = grouped.get(("momentum_only", target_count, horizon,
                                            universe, cutoff))
                    if test and baseline:
                        differences.append(statistics.mean(test) - statistics.mean(baseline))
                if differences:
                    result.append({
                        "target_count": target_count, "horizon": horizon,
                        "universe": universe,
                        "paired_decision_count": len(differences),
                        "mean_difference_vs_momentum": statistics.mean(differences),
                        "positive_difference_rate": statistics.mean(
                            value > 0 for value in differences
                        ),
                    })
    return result


def write_report(output: Path, config_hash: str,
                 coverage: Sequence[Mapping[str, Any]],
                 outcomes: Sequence[Mapping[str, Any]],
                 summaries: Sequence[Mapping[str, Any]],
                 paired: Sequence[Mapping[str, Any]]) -> None:
    rows = [row for row in summaries if row["target_count"] == 10]
    lines = [
        "# Execution Report", "",
        f"- Configuration hash: `{config_hash}`",
        f"- Coverage rows: `{len(coverage)}`",
        f"- Outcome rows: `{len(outcomes)}`", "",
        "## Target Count 10", "",
        "| Variant | Horizon | N | Mean | vs SPY | vs universe | Positive | Concentration |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row['variant']} | {row['horizon']} | {row['observation_count']} | "
            f"{row['mean_return']:.2%} | {row['mean_excess_spy']:.2%} | "
            f"{row['mean_excess_universe']:.2%} | {row['positive_rate']:.2%} | "
            f"{row['max_ticker_concentration']:.2%} |"
        )
    lines += ["", "## Paired Difference vs Momentum, Target Count 10", "",
              "| Horizon | Universe | Decisions | Mean difference | Positive rate |",
              "| ---: | --- | ---: | ---: | ---: |"]
    for row in paired:
        if row["target_count"] == 10:
            lines.append(
                f"| {row['horizon']} | {row['universe']} | "
                f"{row['paired_decision_count']} | "
                f"{row['mean_difference_vs_momentum']:.2%} | "
                f"{row['positive_difference_rate']:.2%} |"
            )
    lines += ["", "## Scope", "",
              "This is the first inspection of the frozen continuous model on the "
              "declared validation window. It is not a portfolio backtest or locked holdout."]
    (output / "execution-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def flatten(config: Mapping[str, Any], digest: str) -> list[dict[str, str]]:
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
