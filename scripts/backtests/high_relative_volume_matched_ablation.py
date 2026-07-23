#!/usr/bin/env python3
"""Matched ablation of the selector's high-relative-volume condition."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = (
    ROOT / "artifacts/stock/backtests/components/selection-models/"
    "high-relative-volume-matched-ablation"
)
VOLUME_FIELD = "is_high_relative_volume"
OTHER_FIELDS = (
    "is_eps_growing",
    "is_profit_margins_increasing",
    "is_revenue_rises",
    "is_debt_lowers",
    "is_institutional_accumalation_rising",
    "is_above_moving_average",
    "is_relative_strength_high",
)
TREATED_SIGNATURE = "|".join(OTHER_FIELDS[:5] + (VOLUME_FIELD,) + OTHER_FIELDS[5:])
CONTROL_SIGNATURE = "|".join(OTHER_FIELDS)
BOOTSTRAP_SEED = 20260723
BOOTSTRAP_SAMPLES = 10000


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--condition-count-artifact", required=True, type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument(
        "--match-scope",
        choices=("per-universe", "combined-universe"),
        default="per-universe",
    )
    args = parser.parse_args(argv)
    source = args.condition_count_artifact.resolve()
    rows = load_source(source / "outcomes.csv")
    matched, excluded = match_cells(rows, args.match_scope)
    summary = summarize(matched)
    subgroups = summarize_subgroups(matched)
    config = {
        "component": "high-relative-volume-matched-ablation",
        "source_artifact": str(source.relative_to(ROOT)),
        "required_other_conditions": OTHER_FIELDS,
        "treatment": VOLUME_FIELD,
        "matching_cell": (
            "universe|window|cutoff|horizon"
            if args.match_scope == "per-universe"
            else "combined-five-universes|window|cutoff|horizon"
        ),
        "match_scope": args.match_scope,
        "within_cell_weighting": "equal_weight_each_group",
        "bootstrap_seed": BOOTSTRAP_SEED,
        "bootstrap_samples": BOOTSTRAP_SAMPLES,
        "source_sha256": file_hash(source / "outcomes.csv"),
    }
    config_hash = hashlib.sha256(
        json.dumps(config, sort_keys=True).encode()
    ).hexdigest()[:8]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%SZ")
    output = args.output_dir or OUTPUT_ROOT / (
        f"{stamp}__matched-seven-condition-base__{config_hash}"
    )
    output.mkdir(parents=True, exist_ok=False)
    write_csv(output / "run_config.csv", flatten_config(config, config_hash))
    write_csv(output / "matched_cells.csv", matched)
    write_csv(output / "summary.csv", summary)
    write_csv(output / "subgroup_summary.csv", subgroups)
    write_csv(output / "excluded_cells.csv", excluded)
    write_report(output, config_hash, rows, matched, excluded, summary, subgroups)
    print(output.relative_to(ROOT))
    return 0


def load_source(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [
            row for row in csv.DictReader(handle)
            if row["signature"] in {TREATED_SIGNATURE, CONTROL_SIGNATURE}
        ]


def match_cells(
    rows: Sequence[Mapping[str, str]],
    match_scope: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    grouped: dict[tuple[str, ...], dict[str, list[Mapping[str, str]]]] = defaultdict(
        lambda: {"treated": [], "control": []}
    )
    for row in rows:
        universe = (
            row["universe"]
            if match_scope == "per-universe"
            else "combined-five-universes"
        )
        key = (universe, row["window"], row["cutoff"], row["horizon"])
        group = "treated" if row["signature"] == TREATED_SIGNATURE else "control"
        grouped[key][group].append(row)
    matched, excluded = [], []
    for key, groups in sorted(grouped.items()):
        treated, control = groups["treated"], groups["control"]
        if not treated or not control:
            excluded.append({
                "universe": key[0],
                "window": key[1],
                "cutoff": key[2],
                "horizon": key[3],
                "treated_count": len(treated),
                "control_count": len(control),
                "reason": "one_group_absent",
            })
            continue
        treated_return = mean(treated, "forward_return")
        control_return = mean(control, "forward_return")
        matched.append({
            "universe": key[0],
            "window": key[1],
            "cutoff": key[2],
            "horizon": int(key[3]),
            "treated_count": len(treated),
            "control_count": len(control),
            "treated_tickers": "|".join(sorted({row["ticker"] for row in treated})),
            "control_tickers": "|".join(sorted({row["ticker"] for row in control})),
            "treated_return": treated_return,
            "control_return": control_return,
            "return_difference": treated_return - control_return,
            "treated_positive_rate": statistics.mean(
                float(row["forward_return"]) > 0 for row in treated
            ),
            "control_positive_rate": statistics.mean(
                float(row["forward_return"]) > 0 for row in control
            ),
            "treated_mae": mean(treated, "max_adverse_excursion"),
            "control_mae": mean(control, "max_adverse_excursion"),
            "mae_difference": (
                mean(treated, "max_adverse_excursion")
                - mean(control, "max_adverse_excursion")
            ),
            "treated_mfe": mean(treated, "max_favorable_excursion"),
            "control_mfe": mean(control, "max_favorable_excursion"),
            "mfe_difference": (
                mean(treated, "max_favorable_excursion")
                - mean(control, "max_favorable_excursion")
            ),
        })
    return matched, excluded


def summarize(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[int(row["horizon"])].append(row)
    result = []
    for horizon, values in sorted(grouped.items()):
        differences = [float(row["return_difference"]) for row in values]
        low, high = bootstrap_interval(differences, horizon)
        result.append({
            "horizon": horizon,
            "matched_cell_count": len(values),
            "treated_observation_count": sum(int(row["treated_count"]) for row in values),
            "control_observation_count": sum(int(row["control_count"]) for row in values),
            "unique_treated_tickers": len({
                ticker for row in values for ticker in str(row["treated_tickers"]).split("|")
            }),
            "unique_control_tickers": len({
                ticker for row in values for ticker in str(row["control_tickers"]).split("|")
            }),
            "treated_mean_return": mean(values, "treated_return"),
            "control_mean_return": mean(values, "control_return"),
            "mean_paired_difference": statistics.mean(differences),
            "median_paired_difference": statistics.median(differences),
            "cells_favoring_treated_rate": statistics.mean(
                difference > 0 for difference in differences
            ),
            "bootstrap_95_low": low,
            "bootstrap_95_high": high,
            "treated_positive_rate": mean(values, "treated_positive_rate"),
            "control_positive_rate": mean(values, "control_positive_rate"),
            "mean_mae_difference": mean(values, "mae_difference"),
            "mean_mfe_difference": mean(values, "mfe_difference"),
        })
    return result


def summarize_subgroups(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, int], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        for dimension, value in (
            ("universe", row["universe"]),
            ("window", row["window"]),
        ):
            grouped[(dimension, str(value), int(row["horizon"]))].append(row)
    result = []
    for (dimension, value, horizon), rows_ in sorted(grouped.items()):
        differences = [float(row["return_difference"]) for row in rows_]
        result.append({
            "dimension": dimension,
            "value": value,
            "horizon": horizon,
            "matched_cell_count": len(rows_),
            "mean_paired_difference": statistics.mean(differences),
            "cells_favoring_treated_rate": statistics.mean(
                difference > 0 for difference in differences
            ),
        })
    return result


def bootstrap_interval(values: Sequence[float], horizon: int) -> tuple[float, float]:
    rng = random.Random(BOOTSTRAP_SEED + horizon)
    means = []
    for _ in range(BOOTSTRAP_SAMPLES):
        sample = [values[rng.randrange(len(values))] for _ in values]
        means.append(statistics.mean(sample))
    means.sort()
    return percentile(means, 0.025), percentile(means, 0.975)


def write_report(
    output: Path,
    config_hash: str,
    source_rows: Sequence[Mapping[str, Any]],
    matched: Sequence[Mapping[str, Any]],
    excluded: Sequence[Mapping[str, Any]],
    summary: Sequence[Mapping[str, Any]],
    subgroups: Sequence[Mapping[str, Any]],
) -> None:
    lines = [
        "# Execution Report", "",
        f"- Configuration hash: `{config_hash}`",
        f"- Relevant source outcome rows: `{len(source_rows)}`",
        f"- Matched cell/horizon rows: `{len(matched)}`",
        f"- Excluded cell/horizon rows: `{len(excluded)}`", "",
        "## Matched Results", "",
        "| Horizon | Cells | Treated obs | Control obs | Treated | Control | Difference | Favor treated | Bootstrap 95% |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in summary:
        lines.append(
            f"| {row['horizon']} | {row['matched_cell_count']} | "
            f"{row['treated_observation_count']} | {row['control_observation_count']} | "
            f"{row['treated_mean_return']:.2%} | {row['control_mean_return']:.2%} | "
            f"{row['mean_paired_difference']:.2%} | "
            f"{row['cells_favoring_treated_rate']:.2%} | "
            f"[{row['bootstrap_95_low']:.2%}, {row['bootstrap_95_high']:.2%}] |"
        )
    lines += [
        "", "## Scope", "",
        "Every matched cell shares universe, window, cutoff, and horizon. Both "
        "groups satisfy the same other seven conditions. This controls date-level "
        "market exposure but remains an observational comparison.",
    ]
    (output / "execution-report.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def mean(rows: Sequence[Mapping[str, Any]], field: str) -> float:
    return statistics.mean(float(row[field]) for row in rows)


def percentile(values: Sequence[float], probability: float) -> float:
    position = (len(values) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    fraction = position - lower
    return values[lower] * (1 - fraction) + values[upper] * fraction


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


if __name__ == "__main__":
    raise SystemExit(main())
