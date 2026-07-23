#!/usr/bin/env python3
"""Run classic 12-1 momentum on dated historical S&P 500 membership."""

from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import importlib.util
import json
import math
import random
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = ROOT / "stages/selection-models/classic_12_1_momentum.py"
MEMBERSHIP_PATH = ROOT / "data/stock/universes/sp500-historical-membership.csv"
INTEGRITY_PATH = ROOT / "data/stock/prices/daily/.integrity.md"
OUTPUT_ROOT = ROOT / (
    "artifacts/stock/backtests/components/selection-models/"
    "classic-12-1-momentum-validation"
)
WINDOW = ("historical-validation-2016-2020", "2016-01-04", "2020-12-31")
HORIZONS = (63, 126, 252)
TARGET_COUNTS = (5, 10, 20, 50)
RANDOM_SEEDS = tuple(range(100))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)
    model = load_module(MODEL_PATH, "classic_momentum_model")
    membership_dates, memberships = load_memberships()
    data_quality_exclusions = load_gap_symbols()
    local_tickers = sorted({
        path.stem
        for path in (ROOT / "data/stock/features/daily").glob("*/*.csv")
    })
    historical_union = {
        normalize_ticker(ticker)
        for date in membership_dates
        if WINDOW[1] <= date <= WINDOW[2]
        for ticker in memberships[date]
    }
    required_tickers = sorted((historical_union & set(local_tickers)) | {"SPY"})
    tapes = {ticker: lean_rows(ticker) for ticker in required_tickers}
    if "SPY" not in tapes:
        raise RuntimeError("SPY tape is required")
    cutoffs = monthly_cutoffs(tapes["SPY"], WINDOW[1], WINDOW[2])
    config = {
        "model": "classic-12-1-momentum",
        "window": WINDOW,
        "frequency": "monthly",
        "horizons": HORIZONS,
        "target_counts": TARGET_COUNTS,
        "random_seeds": RANDOM_SEEDS,
        "membership_source": str(MEMBERSHIP_PATH.relative_to(ROOT)),
        "membership_sha256": file_sha256(MEMBERSHIP_PATH),
        "integrity_sha256": file_sha256(INTEGRITY_PATH),
        "entry": "next_valid_session_adjusted_open",
        "signal": "adj_close[t-21]/adj_close[t-252]-1",
        "data_fingerprint": hashlib.sha256(
            "".join(tapes[ticker]["digest"] for ticker in required_tickers).encode()
        ).hexdigest(),
    }
    digest = hashlib.sha256(
        json.dumps(config, sort_keys=True).encode()
    ).hexdigest()[:8]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%SZ")
    output = args.output_dir or OUTPUT_ROOT / (
        f"{stamp}__historical-membership-2016-2020__{digest}"
    )
    output.mkdir(parents=True, exist_ok=False)

    coverage: list[dict[str, Any]] = []
    rankings: list[dict[str, Any]] = []
    targets: list[dict[str, Any]] = []
    outcomes: list[dict[str, Any]] = []
    bucket_outcomes: list[dict[str, Any]] = []
    random_cohorts: list[dict[str, Any]] = []
    paired: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []
    outcome_cache: dict[tuple[str, str], dict[int, dict[str, Any]]] = {}
    prior_targets: dict[tuple[str, int], set[str]] = {}

    for cutoff in cutoffs:
        snapshot_date, source_members = resolve_membership(
            cutoff, membership_dates, memberships
        )
        candidates = sorted({normalize_ticker(ticker) for ticker in source_members})
        features: dict[str, dict[str, Any]] = {}
        missing_price = []
        for ticker in candidates:
            tape = tapes.get(ticker)
            if (
                ticker in data_quality_exclusions
                or tape is None
                or cutoff not in tape["index"]
            ):
                missing_price.append(ticker)
                continue
            index = tape["index"][cutoff]
            if index < 252:
                continue
            rows = tape["rows"]
            start = rows[index - 252][4]
            end = rows[index - 21][4]
            latest = rows[index][4]
            if start is None or end is None or latest is None or start <= 0:
                continue
            features[ticker] = {
                "ret_252_21": end / start - 1.0,
                "ret_252_0": latest / start - 1.0,
                "start_date": rows[index - 252][0],
                "end_date": rows[index - 21][0],
                "start_adj_close": start,
                "end_adj_close": end,
            }
        spy = cached_outcomes(tapes, "SPY", cutoff, outcome_cache)
        universe = universe_outcomes(
            [ticker for ticker in candidates if ticker not in data_quality_exclusions],
            tapes, cutoff, outcome_cache,
        )
        primary = model.select(
            as_of=cutoff, candidates=candidates, features=features, target_count=50
        )
        validate_result(primary, candidates, 50)
        if snapshot_date > cutoff:
            raise AssertionError("membership snapshot is after decision cutoff")
        coverage.append({
            "cutoff": cutoff,
            "membership_snapshot": snapshot_date,
            "membership_count": len(candidates),
            "local_tape_count": len(candidates) - len(missing_price),
            "eligible_count": len(primary.ranking),
            "missing_local_tape_count": len(missing_price),
            "missing_local_tickers": ",".join(missing_price),
            "data_quality_exclusion_count": sum(
                ticker in data_quality_exclusions for ticker in candidates
            ),
            "data_quality_exclusions": ",".join(
                ticker for ticker in candidates if ticker in data_quality_exclusions
            ),
            "price_coverage": (len(candidates) - len(missing_price)) / len(candidates),
            "explicit_decision_rate": 1.0,
        })
        for row in primary.ranking:
            rankings.append({"cutoff": cutoff, **row})
        emit_buckets(
            cutoff, primary.ranking, tapes, outcome_cache, spy, universe,
            bucket_outcomes,
        )
        variants = {
            "classic_12_1": {
                ticker: {"ret_252_21": row["ret_252_21"]}
                for ticker, row in features.items()
            },
            "momentum_including_latest_month": {
                ticker: {"ret_252_21": row["ret_252_0"]}
                for ticker, row in features.items()
            },
        }
        for variant, variant_features in variants.items():
            for target_count in TARGET_COUNTS:
                result = model.select(
                    as_of=cutoff, candidates=candidates,
                    features=variant_features, target_count=target_count,
                )
                validate_result(result, candidates, target_count)
                repeated = model.select(
                    as_of=cutoff, candidates=candidates,
                    features=variant_features, target_count=target_count,
                )
                if result != repeated:
                    raise AssertionError("selector output is not deterministic")
                selected = {row["instrument_id"] for row in result.targets}
                key = (variant, target_count)
                previous = prior_targets.get(key)
                turnover = (
                    None if previous is None
                    else len(previous.symmetric_difference(selected))
                    / max(1, len(previous) + len(selected))
                )
                prior_targets[key] = selected
                for rank, target in enumerate(result.targets, 1):
                    ticker = target["instrument_id"]
                    targets.append({
                        "cutoff": cutoff, "variant": variant,
                        "target_count": target_count, "rank": rank,
                        "ticker": ticker, "weight": target["weight"],
                        "turnover": turnover,
                    })
                    measured = cached_outcomes(tapes, ticker, cutoff, outcome_cache)
                    for horizon in HORIZONS:
                        value = measured.get(horizon)
                        if value is not None:
                            outcomes.append(outcome_row(
                                cutoff, variant, target_count, rank, ticker,
                                horizon, value, spy, universe,
                            ))
                if variant == "classic_12_1":
                    emit_random_cohorts(
                        cutoff, target_count, result.ranking, tapes, outcome_cache,
                        random_cohorts,
                    )
        paired.extend(paired_for_cutoff(
            cutoff, outcomes, random_cohorts, universe, spy
        ))
        if len(audit) < 12:
            audit.extend(audit_rows(
                cutoff, snapshot_date, candidates, features, primary,
                tapes, outcome_cache, spy, limit=12 - len(audit),
            ))

    summaries = summarize(outcomes)
    buckets = summarize_buckets(bucket_outcomes)
    paired_summary = summarize_paired(paired)
    concentration = concentration_summary(outcomes)
    write_json(output / "configuration.json", {**config, "configuration_hash": digest})
    write_json(output / "input-lineage.json", {
        "membership": str(MEMBERSHIP_PATH.relative_to(ROOT)),
        "membership_sha256": file_sha256(MEMBERSHIP_PATH),
        "feature_root": "data/stock/features/daily",
        "integrity_report": str(INTEGRITY_PATH.relative_to(ROOT)),
        "price_coverage_limitation": (
            "Historical membership is complete for the source tape, but local "
            "price coverage is incomplete for departed and renamed members."
        ),
    })
    write_csv(output / "coverage.csv", coverage)
    write_csv(output / "ranking.csv", rankings)
    write_csv(output / "targets.csv", targets)
    write_csv(output / "forward-outcomes.csv", outcomes)
    write_csv(output / "random-cohorts.csv", random_cohorts)
    write_csv(output / "bucket-summary.csv", buckets)
    write_csv(output / "benchmark-summary.csv", summaries)
    write_csv(output / "paired-comparisons.csv", paired_summary)
    write_csv(output / "concentration-summary.csv", concentration)
    write_csv(output / "audit-samples.csv", audit[:12])
    write_report(output, digest, coverage, summaries, buckets, paired_summary,
                 concentration)
    print(output.relative_to(ROOT))
    return 0


def load_memberships() -> tuple[list[str], dict[str, list[str]]]:
    with MEMBERSHIP_PATH.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return [row["date"] for row in rows], {
        row["date"]: row["tickers"].split(",") for row in rows
    }


def load_gap_symbols() -> set[str]:
    symbols = set()
    in_section = False
    for line in INTEGRITY_PATH.read_text(encoding="utf-8").splitlines():
        if line == "## Supported-Calendar Internal Gaps":
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section and line.startswith("- `"):
            symbols.add(line.split("`", 2)[1])
    return symbols


def resolve_membership(
    cutoff: str, dates: Sequence[str], memberships: Mapping[str, list[str]]
) -> tuple[str, list[str]]:
    position = bisect.bisect_right(dates, cutoff) - 1
    if position < 0:
        raise RuntimeError(f"no membership snapshot for {cutoff}")
    date = dates[position]
    return date, memberships[date]


def normalize_ticker(ticker: str) -> str:
    return ticker.replace(".", "-")


def monthly_cutoffs(tape: Mapping[str, Any], start: str, end: str) -> list[str]:
    months: dict[str, str] = {}
    for row in tape["rows"]:
        date = row[0]
        if start <= date <= end:
            months[date[:7]] = date
    return list(months.values())


def number(value: Any) -> float | None:
    try:
        result = None if value in (None, "") else float(value)
    except (TypeError, ValueError):
        return None
    return result if result is not None and math.isfinite(result) else None


def validate_result(result, candidates, target_count):
    scores = [row["ret_252_21"] for row in result.ranking]
    if scores != sorted(scores, reverse=True):
        raise AssertionError("ranking is not descending by ret_252_21")
    if len({row["instrument_id"] for row in result.ranking}) != len(result.ranking):
        raise AssertionError("duplicate instrument in ranking")
    if len(result.targets) != min(target_count, len(result.ranking)):
        raise AssertionError("selected count does not match contract")
    if result.targets and not math.isclose(
        sum(row["weight"] for row in result.targets), 1.0
    ):
        raise AssertionError("target weights do not sum to one")
    ranked = {row["instrument_id"] for row in result.ranking}
    for ticker, decision in result.eligibility.items():
        if not decision["eligible"] and ticker in ranked:
            raise AssertionError("excluded instrument appears in ranking")
    if set(result.eligibility) != set(candidates):
        raise AssertionError("not every candidate received an eligibility decision")


def lean_rows(ticker: str) -> dict[str, Any]:
    rows = []
    digest = hashlib.sha256()
    for path in sorted((ROOT / "data/stock/features/daily").glob(f"*/{ticker}.csv")):
        with path.open(newline="", encoding="utf-8") as handle:
            for source in csv.DictReader(handle):
                date = source.get("date", "")
                if not ("2015-01-01" <= date <= "2022-01-31"):
                    continue
                values = tuple(number(source.get(field)) for field in (
                    "adj_open", "adj_high", "adj_low", "adj_close"
                ))
                if any(value is None for value in values):
                    continue
                row = (date, values[0], values[1], values[2], values[3])
                rows.append(row)
                digest.update(repr(row).encode())
    rows.sort(key=lambda row: row[0])
    return {
        "rows": rows,
        "index": {row[0]: index for index, row in enumerate(rows)},
        "digest": digest.hexdigest(),
    }


def calculate_outcomes(tape: Mapping[str, Any], cutoff: str) -> dict[int, dict[str, Any]]:
    index = tape["index"].get(cutoff)
    rows = tape["rows"]
    if index is None or index + 1 >= len(rows):
        return {}
    entry_index = index + 1
    entry = rows[entry_index][1]
    if entry <= 0:
        return {}
    result = {}
    lows, highs = [], []
    for position in range(entry_index, min(len(rows), entry_index + max(HORIZONS) + 1)):
        low = rows[position][3]
        high = rows[position][2]
        lows.append(low)
        highs.append(high)
        offset = position - entry_index
        if offset in HORIZONS:
            close = rows[position][4]
            result[offset] = {
                "return": close / entry - 1.0,
                "mae": min(lows) / entry - 1.0,
                "mfe": max(highs) / entry - 1.0,
                "entry_date": rows[entry_index][0],
                "entry_adj_open": entry,
                "outcome_date": rows[position][0],
                "outcome_adj_close": close,
            }
            if not (
                cutoff < result[offset]["entry_date"]
                < result[offset]["outcome_date"]
            ):
                raise AssertionError("forward outcome date alignment failed")
    return result


def cached_outcomes(tapes, ticker, cutoff, cache):
    key = (ticker, cutoff)
    if key not in cache:
        cache[key] = (
            calculate_outcomes(tapes[ticker], cutoff) if ticker in tapes else {}
        )
    return cache[key]


def universe_outcomes(candidates, tapes, cutoff, cache):
    values = defaultdict(list)
    for ticker in candidates:
        for horizon, row in cached_outcomes(tapes, ticker, cutoff, cache).items():
            values[horizon].append(row["return"])
    return {horizon: statistics.mean(rows) for horizon, rows in values.items()}


def outcome_row(cutoff, variant, target_count, rank, ticker, horizon,
                value, spy, universe):
    return {
        "cutoff": cutoff, "variant": variant, "target_count": target_count,
        "rank": rank, "ticker": ticker, "horizon": horizon,
        "forward_return": value["return"], "mae": value["mae"],
        "mfe": value["mfe"],
        "spy_return": spy.get(horizon, {}).get("return"),
        "universe_return": universe.get(horizon),
        "entry_date": value["entry_date"], "outcome_date": value["outcome_date"],
    }


def emit_random_cohorts(cutoff, target_count, ranking, tapes, cache, destination):
    eligible = [row["instrument_id"] for row in ranking]
    count = min(target_count, len(eligible))
    for seed in RANDOM_SEEDS:
        chosen = random.Random(f"{seed}:{cutoff}:{target_count}").sample(
            eligible, count
        ) if count else []
        for horizon in HORIZONS:
            values = [
                measured[horizon]["return"]
                for ticker in chosen
                for measured in [cached_outcomes(tapes, ticker, cutoff, cache)]
                if horizon in measured
            ]
            if values:
                destination.append({
                    "cutoff": cutoff, "target_count": target_count,
                    "seed": seed, "horizon": horizon,
                    "cohort_return": statistics.mean(values),
                    "measured_count": len(values),
                })


def emit_buckets(cutoff, ranking, tapes, cache, spy, universe, destination):
    ordered = list(reversed(ranking))
    count = len(ordered)
    for position, row in enumerate(ordered):
        bucket = min(5, int(position * 5 / max(1, count)) + 1)
        ticker = row["instrument_id"]
        for horizon, value in cached_outcomes(tapes, ticker, cutoff, cache).items():
            if horizon in HORIZONS:
                destination.append({
                    "cutoff": cutoff, "bucket": bucket, "ticker": ticker,
                    "horizon": horizon, "percentile": row["momentum_percentile"],
                    "forward_return": value["return"],
                    "spy_return": spy.get(horizon, {}).get("return"),
                    "universe_return": universe.get(horizon),
                })


def paired_for_cutoff(cutoff, outcomes, random_rows, universe, spy):
    result = []
    current = [row for row in outcomes if row["cutoff"] == cutoff
               and row["variant"] == "classic_12_1"]
    random_current = [row for row in random_rows if row["cutoff"] == cutoff]
    for target_count in TARGET_COUNTS:
        for horizon in HORIZONS:
            selected = [row["forward_return"] for row in current
                        if row["target_count"] == target_count
                        and row["horizon"] == horizon]
            random_values = [row["cohort_return"] for row in random_current
                             if row["target_count"] == target_count
                             and row["horizon"] == horizon]
            if selected and random_values:
                selected_mean = statistics.mean(selected)
                result.append({
                    "cutoff": cutoff, "target_count": target_count,
                    "horizon": horizon, "selection_return": selected_mean,
                    "random_return": statistics.mean(random_values),
                    "difference_vs_random": selected_mean - statistics.mean(random_values),
                    "difference_vs_universe": selected_mean - universe[horizon],
                    "difference_vs_spy": selected_mean - spy[horizon]["return"],
                })
    return result


def summarize(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["variant"], row["target_count"], row["horizon"])].append(row)
    result = []
    for key, group in sorted(grouped.items()):
        returns = [row["forward_return"] for row in group]
        result.append({
            "variant": key[0], "target_count": key[1], "horizon": key[2],
            "observation_count": len(group), "mean_return": statistics.mean(returns),
            "median_return": statistics.median(returns),
            "mean_excess_spy": statistics.mean(
                row["forward_return"] - row["spy_return"] for row in group
            ),
            "mean_excess_universe": statistics.mean(
                row["forward_return"] - row["universe_return"] for row in group
            ),
            "positive_rate": statistics.mean(value > 0 for value in returns),
            "spy_beating_rate": statistics.mean(
                row["forward_return"] > row["spy_return"] for row in group
            ),
            "mean_mae": statistics.mean(row["mae"] for row in group),
            "mean_mfe": statistics.mean(row["mfe"] for row in group),
        })
    return result


def summarize_buckets(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["bucket"], row["horizon"])].append(row)
    by_horizon = defaultdict(list)
    for row in rows:
        by_horizon[row["horizon"]].append(row)
    horizon_diagnostics = {}
    for horizon, horizon_rows in by_horizon.items():
        by_cutoff = defaultdict(list)
        for row in horizon_rows:
            by_cutoff[row["cutoff"]].append(row)
        correlations = [
            spearman(
                [row["percentile"] for row in cutoff_rows],
                [row["forward_return"] for row in cutoff_rows],
            )
            for cutoff_rows in by_cutoff.values()
            if len(cutoff_rows) > 1
        ]
        high = [row["forward_return"] for row in horizon_rows if row["bucket"] == 5]
        low = [row["forward_return"] for row in horizon_rows if row["bucket"] == 1]
        horizon_diagnostics[horizon] = {
            "mean_decision_spearman": statistics.mean(correlations),
            "highest_minus_lowest_spread": statistics.mean(high) - statistics.mean(low),
        }
    result = []
    for key, group in sorted(grouped.items()):
        returns = [row["forward_return"] for row in group]
        result.append({
            "bucket": key[0], "horizon": key[1], "observation_count": len(group),
            "mean_return": statistics.mean(returns),
            "median_return": statistics.median(returns),
            "mean_excess_spy": statistics.mean(
                row["forward_return"] - row["spy_return"] for row in group
            ),
            "mean_excess_universe": statistics.mean(
                row["forward_return"] - row["universe_return"] for row in group
            ),
            **horizon_diagnostics[key[1]],
        })
    return result


def spearman(xs, ys):
    def ranks(values):
        order = sorted(range(len(values)), key=lambda i: values[i])
        result = [0.0] * len(values)
        for rank, index in enumerate(order):
            result[index] = rank
        return result
    rx, ry = ranks(xs), ranks(ys)
    mx, my = statistics.mean(rx), statistics.mean(ry)
    numerator = sum((x - mx) * (y - my) for x, y in zip(rx, ry))
    denominator = math.sqrt(
        sum((x - mx) ** 2 for x in rx) * sum((y - my) ** 2 for y in ry)
    )
    return numerator / denominator if denominator else 0.0


def summarize_paired(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["target_count"], row["horizon"])].append(row)
    result = []
    for key, group in sorted(grouped.items()):
        result.append({
            "target_count": key[0], "horizon": key[1],
            "decision_count": len(group),
            "mean_difference_vs_random": statistics.mean(
                row["difference_vs_random"] for row in group
            ),
            "positive_vs_random_rate": statistics.mean(
                row["difference_vs_random"] > 0 for row in group
            ),
            "mean_difference_vs_universe": statistics.mean(
                row["difference_vs_universe"] for row in group
            ),
            "mean_difference_vs_spy": statistics.mean(
                row["difference_vs_spy"] for row in group
            ),
            "positive_vs_spy_rate": statistics.mean(
                row["difference_vs_spy"] > 0 for row in group
            ),
        })
    return result


def concentration_summary(rows):
    group = [row for row in rows if row["variant"] == "classic_12_1"
             and row["target_count"] == 10 and row["horizon"] == 126]
    counts = Counter(row["ticker"] for row in group)
    return [
        {"ticker": ticker, "observation_count": count,
         "concentration": count / len(group)}
        for ticker, count in counts.most_common()
    ]


def audit_rows(cutoff, snapshot, candidates, features, result, tapes, cache, spy, limit):
    selected = {row["instrument_id"] for row in result.targets[:10]}
    ranked = {row["instrument_id"]: row for row in result.ranking}
    ordered = (
        list(selected)[:3]
        + [row["instrument_id"] for row in result.ranking if row["instrument_id"] not in selected][:3]
        + [ticker for ticker in candidates if ticker not in features][:2]
    )
    output = []
    for ticker in ordered[:limit]:
        feature = features.get(ticker, {})
        rank = ranked.get(ticker, {})
        measured = cached_outcomes(tapes, ticker, cutoff, cache).get(126, {})
        output.append({
            "ticker": ticker, "membership_snapshot": snapshot, "cutoff": cutoff,
            "eligible": ticker in ranked, "selected": ticker in selected,
            "exclusion_reason": "" if ticker in ranked else "missing_feature_or_price",
            "start_date": feature.get("start_date"),
            "end_date": feature.get("end_date"),
            "start_adj_close": feature.get("start_adj_close"),
            "end_adj_close": feature.get("end_adj_close"),
            "manual_ret_252_21": (
                feature.get("end_adj_close") / feature.get("start_adj_close") - 1
                if feature else None
            ),
            "stored_ret_252_21": feature.get("ret_252_21"),
            "percentile": rank.get("momentum_percentile"),
            "rating": rank.get("rating"), "rank": rank.get("rank"),
            "entry_date": measured.get("entry_date"),
            "entry_adj_open": measured.get("entry_adj_open"),
            "outcome_date": measured.get("outcome_date"),
            "outcome_adj_close": measured.get("outcome_adj_close"),
            "forward_return_126": measured.get("return"),
            "spy_return_126": spy.get(126, {}).get("return"),
        })
    return output


def write_report(output, digest, coverage, summaries, buckets, paired, concentration):
    primary = [row for row in summaries if row["variant"] == "classic_12_1"
               and row["target_count"] == 10]
    lines = [
        "# Classic 12-1 Momentum Execution Report", "",
        f"- Configuration hash: `{digest}`",
        f"- Decisions: `{len(coverage)}`",
        f"- Mean historical membership price coverage: "
        f"`{statistics.mean(row['price_coverage'] for row in coverage):.2%}`",
        "- Limitation: historical membership is point-in-time, but unavailable "
        "departed-member prices leave residual survivorship bias.", "",
        "## Primary Target Count 10", "",
        "| Horizon | N | Mean | vs SPY | vs universe |",
        "| ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in primary:
        lines.append(
            f"| {row['horizon']} | {row['observation_count']} | "
            f"{row['mean_return']:.2%} | {row['mean_excess_spy']:.2%} | "
            f"{row['mean_excess_universe']:.2%} |"
        )
    lines += ["", "## Paired Comparisons", "",
              "| Horizon | vs random | Positive vs random | vs universe | vs SPY |",
              "| ---: | ---: | ---: | ---: | ---: |"]
    for row in paired:
        if row["target_count"] == 10:
            lines.append(
                f"| {row['horizon']} | {row['mean_difference_vs_random']:.2%} | "
                f"{row['positive_vs_random_rate']:.2%} | "
                f"{row['mean_difference_vs_universe']:.2%} | "
                f"{row['mean_difference_vs_spy']:.2%} |"
            )
    lines += ["", "## Momentum Buckets", "",
              "| Bucket | Horizon | N | Mean | vs universe | Mean decision Spearman |",
              "| ---: | ---: | ---: | ---: | ---: | ---: |"]
    for row in buckets:
        if row["horizon"] in (63, 126):
            lines.append(
                f"| {row['bucket']} | {row['horizon']} | {row['observation_count']} | "
                f"{row['mean_return']:.2%} | {row['mean_excess_universe']:.2%} | "
                f"{row['mean_decision_spearman']:.3f} |"
            )
    if concentration:
        lines += ["", f"Maximum ticker concentration at 126 sessions: "
                  f"`{concentration[0]['concentration']:.2%}` "
                  f"({concentration[0]['ticker']})."]
    (output / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    write_json(output / "execution-report.json", {
        "configuration_hash": digest,
        "decision_count": len(coverage),
        "mean_price_coverage": statistics.mean(
            row["price_coverage"] for row in coverage
        ),
        "primary_summary": primary,
        "paired_summary": [row for row in paired if row["target_count"] == 10],
        "maximum_ticker_concentration": (
            concentration[0]["concentration"] if concentration else None
        ),
        "promotion_eligible": False,
        "promotion_blocker": "incomplete historical price coverage",
    })


def file_sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path, rows):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    raise SystemExit(main())
