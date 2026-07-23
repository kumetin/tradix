#!/usr/bin/env python3
"""Benchmark exit policies on immutable selector entry tapes."""

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
FEATURE_ROOT = ROOT / "data/stock/features/daily"
OUTPUT_ROOT = (
    ROOT / "artifacts/stock/backtests/components/portfolio-policies/"
    "partial-profit-breakeven-time-exit"
)
POLICY_PATH = (
    ROOT / "stages/portfolio-policies/partial_profit_breakeven_time_exit.py"
)
ENTRY_SOURCES = {
    "full",
    "unfiltered",
    "fundamental_only",
    "technical_demand_only",
}
VARIANTS = (
    "full_hold",
    "full_profit_liquidation",
    "fixed_stop_only",
    "partial_profit_no_stagnation",
    "partial_profit_breakeven_time_exit",
)
MAX_SESSIONS = 378


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entry-artifact", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)
    artifact = args.entry_artifact.resolve()
    entries = load_entries(artifact / "outcomes.csv")
    tickers = sorted({entry["ticker"] for entry in entries})
    tapes = {ticker: load_tape(ticker) for ticker in tickers}
    policy = load_module(POLICY_PATH)
    fingerprint = input_fingerprint(artifact, tickers)
    config = {
        "component": "partial-profit-breakeven-time-exit",
        "entry_artifact": str(artifact.relative_to(ROOT)),
        "entry_sources": sorted(ENTRY_SOURCES),
        "target_count": 10,
        "variants": VARIANTS,
        "maximum_holding_sessions": MAX_SESSIONS,
        "common_history_requirement": "379 post-entry valid sessions for every variant",
        "time_exit_fill": "next_valid_adjusted_open",
        "data_fingerprint": fingerprint,
    }
    config_hash = hashlib.sha256(
        json.dumps(config, sort_keys=True).encode()
    ).hexdigest()[:8]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%SZ")
    output = args.output_dir or OUTPUT_ROOT / (
        f"{stamp}__selector-entry-tapes__{config_hash}"
    )
    output.mkdir(parents=True, exist_ok=False)

    outcomes = []
    exclusions = []
    for entry in entries:
        tape = tapes[entry["ticker"]]
        index = tape["index"].get(entry["cutoff"])
        if index is None or index + 1 >= len(tape["rows"]):
            exclusions.append({**entry, "reason": "missing_next_session_entry"})
            continue
        entry_index = index + 1
        entry_price = number(tape["rows"][entry_index].get("adj_open"))
        if entry_price is None:
            exclusions.append({**entry, "reason": "invalid_entry_open"})
            continue
        if entry_index + MAX_SESSIONS + 1 >= len(tape["rows"]):
            exclusions.append({**entry, "reason": "insufficient_common_exit_history"})
            continue
        for variant in VARIANTS:
            result = simulate(
                variant=variant,
                ticker=entry["ticker"],
                cutoff=entry["cutoff"],
                rows=tape["rows"],
                entry_index=entry_index,
                entry_price=entry_price,
                policy=policy,
            )
            if result is None:
                exclusions.append({**entry, "variant": variant, "reason": "insufficient_exit_history"})
            else:
                outcomes.append({**entry, "variant": variant, **result})

    summaries = summarize(outcomes, exclusions)
    write_csv(output / "run_config.csv", flatten_config(config, config_hash))
    write_csv(output / "entries.csv", entries)
    write_csv(output / "outcomes.csv", outcomes)
    write_csv(output / "exclusions.csv", exclusions)
    write_csv(output / "summary.csv", summaries)
    write_report(output, config_hash, entries, outcomes, exclusions, summaries)
    print(output.relative_to(ROOT))
    return 0


def load_entries(path: Path) -> list[dict[str, str]]:
    unique = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if (
                row["variant"] in ENTRY_SOURCES
                and row["target_count"] == "10"
                and row["horizon"] == "21"
            ):
                key = (
                    row["variant"], row["universe"], row["window"],
                    row["cutoff"], row["ticker"],
                )
                unique[key] = {
                    "entry_source": row["variant"],
                    "universe": row["universe"],
                    "window": row["window"],
                    "cutoff": row["cutoff"],
                    "ticker": row["ticker"],
                    "selection_rank": row["rank"],
                }
    return [unique[key] for key in sorted(unique)]


def simulate(
    *,
    variant: str,
    ticker: str,
    cutoff: str,
    rows: Sequence[Mapping[str, str]],
    entry_index: int,
    entry_price: float,
    policy: Any,
) -> dict[str, Any] | None:
    remaining = 1.0
    realized = 0.0
    partial_filled = False
    exit_legs = 0
    target_filled = False
    gap_loss = 0.0
    min_equity = 1.0
    max_equity = 1.0
    final_reason = ""
    final_session = 0

    for session in range(1, MAX_SESSIONS + 1):
        row_index = entry_index + session
        if row_index >= len(rows):
            return None
        row = rows[row_index]
        bar = parsed_bar(row)
        if bar is None:
            return None
        open_price, high, low, close = bar
        min_equity = min(min_equity, (realized + remaining * low) / entry_price)
        max_equity = max(max_equity, (realized + remaining * high) / entry_price)

        if variant == "partial_profit_breakeven_time_exit":
            result = policy.transition(
                as_of=row["date"],
                selection_intent=[],
                portfolio_state=[{
                    "instrument_id": ticker,
                    "entry_price": entry_price,
                    "original_quantity": 1.0,
                    "remaining_quantity": remaining,
                    "partial_profit_filled": partial_filled,
                }],
                cash_state={"settled": 1.0},
                daily_market_state={ticker: {
                    "open": open_price, "high": high, "low": low, "close": close,
                }},
                session_index={ticker: session},
            )
            actionable = [
                order for order in result.orders
                if order["side"] == "sell" and (
                    "expected_fill_price" in order
                    or order["reason"] in {"stagnation_exit", "maximum_holding_exit"}
                )
            ]
            if actionable:
                order = actionable[0]
                quantity = float(order["quantity"])
                if "expected_fill_price" in order:
                    fill = float(order["expected_fill_price"])
                else:
                    fill = next_open(rows, row_index)
                    if fill is None:
                        return None
                realized += quantity * fill
                remaining -= quantity
                exit_legs += 1
                final_reason = order["reason"]
                final_session = session + (0 if "expected_fill_price" in order else 1)
                if order["reason"] == "partial_profit":
                    target_filled = True
                    partial_filled = True
                else:
                    if order["reason"] in {"initial_stop", "breakeven_stop"}:
                        gap_loss += max(0.0, float(order["stop_price"]) - fill)
                    remaining = 0.0
            if remaining <= 1e-12:
                break
            continue

        stop = None
        target = None
        if variant == "full_profit_liquidation":
            target = entry_price * 1.225
        elif variant == "fixed_stop_only":
            stop = entry_price * 0.925
        elif variant == "partial_profit_no_stagnation":
            stop = entry_price if partial_filled else entry_price * 0.925
            target = None if partial_filled else entry_price * 1.225

        if stop is not None and low <= stop:
            fill = min(open_price, stop)
            realized += remaining * fill
            gap_loss += max(0.0, stop - fill) * remaining
            remaining = 0.0
            exit_legs += 1
            final_reason = "breakeven_stop" if partial_filled else "initial_stop"
            final_session = session
            break
        if target is not None and high >= target:
            fill = max(open_price, target)
            quantity = remaining if variant == "full_profit_liquidation" else 0.5
            realized += quantity * fill
            remaining -= quantity
            exit_legs += 1
            target_filled = True
            partial_filled = variant == "partial_profit_no_stagnation"
            final_reason = (
                "full_profit_target"
                if variant == "full_profit_liquidation"
                else "partial_profit"
            )
            final_session = session
            if remaining <= 1e-12:
                break

        if session == MAX_SESSIONS:
            fill = next_open(rows, row_index)
            if fill is None:
                return None
            realized += remaining * fill
            remaining = 0.0
            exit_legs += 1
            final_reason = "maximum_holding_exit"
            final_session = session + 1
            break

    if remaining > 1e-12:
        return None
    trade_return = realized / entry_price - 1.0
    annualized = (
        (1.0 + trade_return) ** (252.0 / max(1, final_session)) - 1.0
        if trade_return > -1.0 else -1.0
    )
    return {
        "entry_date": rows[entry_index]["date"],
        "entry_price": entry_price,
        "exit_reason": final_reason,
        "holding_sessions": final_session,
        "exit_legs": exit_legs,
        "target_filled": target_filled,
        "trade_return": trade_return,
        "annualized_return": annualized,
        "max_adverse_excursion": min_equity - 1.0,
        "max_favorable_excursion": max_equity - 1.0,
        "gap_loss_return": gap_loss / entry_price,
        "cash_conservation_error": abs(realized - entry_price * (1.0 + trade_return)),
        "quantity_conservation_error": abs(1.0 - (1.0 - remaining)),
    }


def summarize(
    outcomes: Sequence[Mapping[str, Any]],
    exclusions: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in outcomes:
        grouped[(row["entry_source"], row["variant"])].append(row)
    result = []
    for (source, variant), rows in sorted(grouped.items()):
        returns = [float(row["trade_return"]) for row in rows]
        reasons = defaultdict(int)
        for row in rows:
            reasons[row["exit_reason"]] += 1
        result.append({
            "entry_source": source,
            "variant": variant,
            "trade_count": len(rows),
            "mean_return": statistics.mean(returns),
            "median_return": statistics.median(returns),
            "p05_return": percentile(returns, 0.05),
            "positive_rate": statistics.mean(value > 0 for value in returns),
            "mean_annualized_return": statistics.mean(
                float(row["annualized_return"]) for row in rows
            ),
            "mean_mae": statistics.mean(
                float(row["max_adverse_excursion"]) for row in rows
            ),
            "mean_mfe": statistics.mean(
                float(row["max_favorable_excursion"]) for row in rows
            ),
            "mean_holding_sessions": statistics.mean(
                int(row["holding_sessions"]) for row in rows
            ),
            "mean_exit_legs": statistics.mean(int(row["exit_legs"]) for row in rows),
            "target_rate": statistics.mean(bool(row["target_filled"]) for row in rows),
            "initial_stop_rate": reasons["initial_stop"] / len(rows),
            "breakeven_stop_rate": reasons["breakeven_stop"] / len(rows),
            "stagnation_exit_rate": reasons["stagnation_exit"] / len(rows),
            "horizon_exit_rate": reasons["maximum_holding_exit"] / len(rows),
            "mean_gap_loss_return": statistics.mean(
                float(row["gap_loss_return"]) for row in rows
            ),
            "max_cash_conservation_error": max(
                float(row["cash_conservation_error"]) for row in rows
            ),
            "max_quantity_conservation_error": max(
                float(row["quantity_conservation_error"]) for row in rows
            ),
        })
    return result


def write_report(
    output: Path,
    config_hash: str,
    entries: Sequence[Mapping[str, Any]],
    outcomes: Sequence[Mapping[str, Any]],
    exclusions: Sequence[Mapping[str, Any]],
    summaries: Sequence[Mapping[str, Any]],
) -> None:
    lines = [
        "# Execution Report", "",
        f"- Configuration hash: `{config_hash}`",
        f"- Unique source entries: `{len(entries)}`",
        f"- Completed variant outcomes: `{len(outcomes)}`",
        f"- Exclusions: `{len(exclusions)}`", "",
        "## Results", "",
        "| Entry source | Variant | Trades | Mean | P05 | Positive | MAE | Sessions |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summaries:
        lines.append(
            f"| {row['entry_source']} | {row['variant']} | {row['trade_count']} | "
            f"{row['mean_return']:.2%} | {row['p05_return']:.2%} | "
            f"{row['positive_rate']:.2%} | {row['mean_mae']:.2%} | "
            f"{row['mean_holding_sessions']:.1f} |"
        )
    lines += [
        "", "## Scope", "",
        "This is an isolated trade-path benchmark. Entry cohorts overlap, capital "
        "is not redeployed, and no fees, slippage, settlement, portfolio CAGR, "
        "portfolio drawdown, or portfolio cash drag is modeled.",
    ]
    (output / "execution-report.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def load_tape(ticker: str) -> dict[str, Any]:
    rows = []
    for path in sorted(FEATURE_ROOT.glob(f"*/{ticker}.csv")):
        with path.open(newline="", encoding="utf-8") as handle:
            rows.extend(csv.DictReader(handle))
    rows = [row for row in rows if row.get("date") and row.get("adj_open")]
    rows.sort(key=lambda row: row["date"])
    return {"rows": rows, "index": {row["date"]: i for i, row in enumerate(rows)}}


def parsed_bar(row: Mapping[str, str]) -> tuple[float, float, float, float] | None:
    values = tuple(number(row.get(field)) for field in (
        "adj_open", "adj_high", "adj_low", "adj_close"
    ))
    return None if any(value is None for value in values) else values


def next_open(rows: Sequence[Mapping[str, str]], index: int) -> float | None:
    return number(rows[index + 1].get("adj_open")) if index + 1 < len(rows) else None


def input_fingerprint(artifact: Path, tickers: Sequence[str]) -> str:
    digest = hashlib.sha256()
    paths = [artifact / "outcomes.csv"]
    paths.extend(
        path for path in FEATURE_ROOT.glob("*/*.csv") if path.stem in set(tickers)
    )
    for path in sorted(paths):
        digest.update(str(path).encode())
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


def percentile(values: Sequence[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def number(value: Any) -> float | None:
    try:
        return None if value in (None, "") else float(value)
    except (TypeError, ValueError):
        return None


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location(
        "partial_profit_breakeven_time_exit_benchmark_policy", path
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    raise SystemExit(main())
