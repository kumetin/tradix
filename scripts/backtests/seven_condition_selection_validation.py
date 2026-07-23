#!/usr/bin/env python3
"""Validate the frozen seven-condition selector on an unused window."""

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
MODEL_PATH = ROOT / "stages/selection-models/fundamental_technical_momentum.py"
OUTPUT_ROOT = (
    ROOT / "artifacts/stock/backtests/components/selection-models/"
    "fundamental-technical-seven-condition-validation"
)
WINDOW = ("validation-2025h1", "2025-02-03", "2025-07-18")
HORIZONS = (21, 63, 126, 252)
TARGET_COUNTS = (1, 5, 10, 20)
VARIANTS = ("seven_condition", "strict_eight_condition", "unfiltered")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)
    base = load_module(BASE_PATH, "seven_validation_base")
    model = load_module(MODEL_PATH, "seven_validation_model")
    universes = {
        path.stem: base._universe(path)
        for path in sorted((ROOT / "configuration/universes").glob("random-sp500-50-*.md"))
    }
    tickers = sorted({ticker for values in universes.values() for ticker in values} | {"SPY"})
    tapes = {ticker: base._rows(ticker) for ticker in tickers}
    config = {
        "model": "fundamental-technical-momentum-seven-condition",
        "window": WINDOW,
        "horizons": HORIZONS,
        "target_counts": TARGET_COUNTS,
        "variants": VARIANTS,
        "universes": universes,
        "data_fingerprint": base._data_fingerprint(tickers),
    }
    config_hash = hashlib.sha256(
        json.dumps(config, sort_keys=True).encode()
    ).hexdigest()[:8]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%SZ")
    output = args.output_dir or OUTPUT_ROOT / (
        f"{stamp}__unused-2025h1__{config_hash}"
    )
    output.mkdir(parents=True, exist_ok=False)
    coverage, outcomes = [], []
    cache: dict[tuple[str, str], dict[int, dict[str, float]]] = {}
    for universe_name, candidates in universes.items():
        cutoffs = base._weekly_cutoffs(tapes["SPY"], WINDOW[1], WINDOW[2])
        for cutoff in cutoffs:
            features = {
                ticker: tapes[ticker]["by_date"].get(cutoff)
                for ticker in candidates
                if cutoff in tapes[ticker]["by_date"]
            }
            spy = base._cached_outcomes(tapes, "SPY", cutoff, cache)
            universe_returns = {
                horizon: value
                for horizon, value in base._universe_outcomes(
                    candidates, tapes, cutoff, cache
                ).items()
                if horizon in HORIZONS
            }
            for variant in VARIANTS:
                variant_features = (
                    {
                        ticker: {
                            **row,
                            **{field: "true" for field in model.BOOLEAN_FIELDS},
                        }
                        for ticker, row in features.items()
                    }
                    if variant == "unfiltered"
                    else features
                )
                select_fn = (
                    model.select_without_high_relative_volume
                    if variant == "seven_condition"
                    else model.select
                )
                for target_count in TARGET_COUNTS:
                    result = select_fn(
                        as_of=cutoff,
                        candidates=candidates,
                        features=variant_features,
                        target_count=target_count,
                    )
                    coverage.append({
                        "universe": universe_name,
                        "window": WINDOW[0],
                        "cutoff": cutoff,
                        "variant": variant,
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
                                "universe": universe_name,
                                "window": WINDOW[0],
                                "cutoff": cutoff,
                                "variant": variant,
                                "target_count": target_count,
                                "rank": rank,
                                "ticker": ticker,
                                "horizon": horizon,
                                "forward_return": outcome["return"],
                                "max_adverse_excursion": outcome["mae"],
                                "max_favorable_excursion": outcome["mfe"],
                                "spy_return": spy.get(horizon, {}).get("return"),
                                "universe_return": universe_returns.get(horizon),
                            })
    summaries = summarize(outcomes, coverage)
    write_csv(output / "run_config.csv", flatten(config, config_hash))
    write_csv(output / "coverage.csv", coverage)
    write_csv(output / "outcomes.csv", outcomes)
    write_csv(output / "summary.csv", summaries)
    write_report(output, config_hash, coverage, outcomes, summaries)
    print(output.relative_to(ROOT))
    return 0


def summarize(
    outcomes: Sequence[Mapping[str, Any]],
    coverage: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, int, int], list[Mapping[str, Any]]] = defaultdict(list)
    for row in outcomes:
        grouped[(row["variant"], int(row["target_count"]), int(row["horizon"]))].append(row)
    result = []
    for key, rows in sorted(grouped.items()):
        returns = [float(row["forward_return"]) for row in rows]
        result.append({
            "variant": key[0],
            "target_count": key[1],
            "horizon": key[2],
            "observation_count": len(rows),
            "selection_decision_count": len({
                (row["universe"], row["cutoff"]) for row in rows
            }),
            "unique_tickers": len({row["ticker"] for row in rows}),
            "max_ticker_concentration": max(
                sum(row["ticker"] == ticker for row in rows) / len(rows)
                for ticker in {row["ticker"] for row in rows}
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
            "mean_mae": statistics.mean(
                float(row["max_adverse_excursion"]) for row in rows
            ),
            "mean_mfe": statistics.mean(
                float(row["max_favorable_excursion"]) for row in rows
            ),
        })
    return result


def write_report(
    output: Path,
    config_hash: str,
    coverage: Sequence[Mapping[str, Any]],
    outcomes: Sequence[Mapping[str, Any]],
    summaries: Sequence[Mapping[str, Any]],
) -> None:
    rows = [row for row in summaries if row["target_count"] == 10]
    lines = [
        "# Execution Report", "",
        f"- Configuration hash: `{config_hash}`",
        f"- Coverage rows: `{len(coverage)}`",
        f"- Outcome rows: `{len(outcomes)}`", "",
        "## Target Count 10", "",
        "| Variant | Horizon | Observations | Mean | vs SPY | vs universe | Positive | Concentration |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row['variant']} | {row['horizon']} | {row['observation_count']} | "
            f"{row['mean_return']:.2%} | {row['mean_excess_spy']:.2%} | "
            f"{row['mean_excess_universe']:.2%} | {row['positive_rate']:.2%} | "
            f"{row['max_ticker_concentration']:.2%} |"
        )
    lines += [
        "", "## Scope", "",
        "This is the first inspection of the frozen seven-condition model on the "
        "declared validation window. It is not a portfolio backtest or locked holdout.",
    ]
    (output / "execution-report.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


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
