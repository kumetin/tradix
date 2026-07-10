#!/usr/bin/env python3
"""Validate static platform profile markdown files.

This is intentionally lightweight: it checks the contracts documented in
``tests/validation/static-profiles.md`` without requiring a full backtest engine.
"""

from __future__ import annotations

import datetime as dt
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

RECOGNIZED_REBALANCE = {"daily", "weekly", "monthly", "quarterly"}


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.passes: list[str] = []

    def pass_(self, message: str) -> None:
        self.passes.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def error(self, message: str) -> None:
        self.errors.append(message)

    def print(self) -> None:
        for message in self.passes:
            print(f"PASS {message}")
        for message in self.warnings:
            print(f"WARN {message}")
        for message in self.errors:
            print(f"FAIL {message}")
        print()
        print(
            f"Summary: {len(self.passes)} pass, "
            f"{len(self.warnings)} warn, {len(self.errors)} fail"
        )


def main() -> int:
    report = Report()
    validate_universes(report)
    validate_funding(report)
    validate_schedules(report)
    validate_evaluations(report)
    validate_backtests(report)
    validate_component_benchmarks(report)
    report.print()
    return 1 if report.errors else 0


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def profile_files(directory: str) -> list[Path]:
    base = ROOT / directory
    return sorted(path for path in base.glob("*.md") if path.name != "README.md")


def extract_section(text: str, heading: str) -> str:
    pattern = re.compile(
        r"^## " + re.escape(heading) + r"\s*$([\s\S]*?)(?=^## |\Z)",
        re.MULTILINE,
    )
    match = pattern.search(text)
    return match.group(1) if match else ""


def extract_inline_code_after_heading(text: str, heading: str) -> str | None:
    section = extract_section(text, heading)
    match = re.search(r"`([^`]+)`", section)
    return match.group(1) if match else None


def extract_bullets(section: str) -> list[str]:
    return [match.group(1).strip() for match in re.finditer(r"^- `([^`]+)`", section, re.M)]


def extract_table_value(text: str, key: str) -> str | None:
    match = re.search(r"^\| `" + re.escape(key) + r"` \| ([^|]+) \|", text, re.M)
    return match.group(1).strip()


def parse_money(value: str | None) -> float | None:
    if value is None:
        return None
    clean = value.replace("`", "").replace("$", "").replace(",", "").strip()
    try:
        return float(clean)
    except ValueError:
        return None


def parse_date(value: str | None) -> dt.date | None:
    if value is None:
        return None
    value = value.strip("` ")
    try:
        return dt.date.fromisoformat(value)
    except ValueError:
        return None


def validate_universes(report: Report) -> None:
    symbols_available = available_price_symbols()
    for path in profile_files("universes"):
        text = read(path)
        fallback = extract_inline_code_after_heading(text, "Fallback Ticker")
        tickers = extract_bullets(extract_section(text, "Tickers"))
        label = rel(path)

        if tickers:
            report.pass_(f"{label}: universe has {len(tickers)} tickers")
        else:
            report.error(f"{label}: universe has no tickers")

        duplicates = sorted({ticker for ticker in tickers if tickers.count(ticker) > 1})
        if duplicates:
            report.error(f"{label}: duplicate tickers: {', '.join(duplicates)}")
        else:
            report.pass_(f"{label}: no duplicate tickers")

        if fallback and fallback in tickers:
            report.pass_(f"{label}: fallback ticker {fallback} is in universe")
        else:
            report.error(f"{label}: fallback ticker missing or not in universe")

        missing = sorted(ticker for ticker in tickers if ticker not in symbols_available)
        if missing:
            report.error(f"{label}: tickers missing from local daily price dataset: {', '.join(missing)}")
        else:
            report.pass_(f"{label}: all tickers exist in local daily price dataset")


def available_price_symbols() -> set[str]:
    base = ROOT / "data/stock/prices/daily"
    return {path.stem for path in base.glob("*/*.csv")}


def validate_funding(report: Report) -> None:
    for path in profile_files("funding"):
        text = read(path)
        label = rel(path)
        initial = parse_money(extract_table_value(text, "initial_lump_sum"))
        monthly = parse_money(extract_table_value(text, "monthly_contribution"))

        if initial is None or initial < 0:
            report.error(f"{label}: invalid initial_lump_sum")
        else:
            report.pass_(f"{label}: initial_lump_sum is non-negative")

        if monthly is None or monthly < 0:
            report.error(f"{label}: invalid monthly_contribution")
        else:
            report.pass_(f"{label}: monthly_contribution is non-negative")

        if "Only" in title(text) and monthly != 0:
            report.error(f"{label}: initial-only profile must have monthly_contribution $0")


def validate_schedules(report: Report) -> None:
    for path in profile_files("schedules"):
        text = read(path)
        label = rel(path)
        value = extract_table_value(text, "rebalance_frequency")
        frequency = (value or "").lower()
        if frequency in RECOGNIZED_REBALANCE:
            report.pass_(f"{label}: recognized rebalance_frequency {value}")
        else:
            report.error(f"{label}: unrecognized rebalance_frequency {value!r}")

        if re.search(r"data available before|signal cutoff|known before", text, re.I):
            report.pass_(f"{label}: signal cutoff language present")
        else:
            report.warn(f"{label}: signal cutoff language not found")


def validate_evaluations(report: Report) -> None:
    for path in sorted((ROOT / "evaluations").glob("*/*.md")):
        text = read(path)
        label = rel(path)
        warmup = parse_date(extract_table_value(text, "warmup_start"))
        start = parse_date(extract_table_value(text, "evaluation_start"))
        end = parse_date(extract_table_value(text, "evaluation_end"))
        if warmup and start and end and warmup <= start <= end:
            report.pass_(f"{label}: date order is valid")
        else:
            report.error(f"{label}: invalid warmup/evaluation date order")

        if re.search(r"warm-?up|reported performance|metrics", text, re.I):
            report.pass_(f"{label}: warm-up/evaluation distinction mentioned")
        else:
            report.warn(f"{label}: warm-up exclusion not mentioned in profile")

        split_method = extract_table_value(text, "split_method") or ""
        if re.search(r"locked|holdout", split_method, re.I):
            if re.search(r"locked|holdout", text, re.I):
                report.pass_(f"{label}: holdout labeling mentioned")
            else:
                report.warn(f"{label}: holdout split lacks explicit holdout labeling")
        else:
            report.pass_(f"{label}: no locked holdout configured")


def validate_backtests(report: Report) -> None:
    for path in sorted((ROOT / "backtests").glob("*/*.md")):
        text = read(path)
        label = rel(path)
        links = markdown_links(text)
        missing_links = []
        linked_files = []
        for _, href in links:
            if href.startswith("http"):
                continue
            target = (path.parent / href).resolve()
            linked_files.append(target)
            if not target.exists():
                missing_links.append(href)
        if missing_links:
            report.error(f"{label}: missing linked files: {', '.join(missing_links)}")
        else:
            report.pass_(f"{label}: linked profile files resolve")

        selection = linked_path_containing(linked_files, "selection-models")
        policy = linked_path_containing(linked_files, "portfolio-policies")
        execution = linked_path_containing(linked_files, "execution-models")

        if selection and policy:
            validate_selection_policy_compat(report, label, selection, policy)
        else:
            report.error(f"{label}: missing selection model or portfolio policy link")

        if policy and execution:
            validate_policy_execution_compat(report, label, policy, execution)
        else:
            report.error(f"{label}: missing portfolio policy or execution model link")

        benchmark_section = extract_section(text, "Benchmarks")
        if re.search(r"\bSPY\b", benchmark_section) and re.search(
            r"equal-weight", benchmark_section, re.I
        ):
            report.pass_(f"{label}: benchmark declaration present")
        else:
            report.warn(f"{label}: no benchmark declaration in backtest spec")


def validate_component_benchmarks(report: Report) -> None:
    base = ROOT / "component-benchmarks"
    if not base.exists():
        report.warn("component-benchmarks: directory does not exist")
        return

    for path in sorted(base.glob("*/*.md")):
        text = read(path)
        label = rel(path)
        links = markdown_links(text)
        missing_links = []
        linked_files = []
        for _, href in links:
            if href.startswith("http"):
                continue
            target = (path.parent / href).resolve()
            linked_files.append(target)
            if not target.exists():
                missing_links.append(href)
        if missing_links:
            report.error(f"{label}: missing linked files: {', '.join(missing_links)}")
        else:
            report.pass_(f"{label}: linked profile files resolve")

        component_type = extract_inline_code_after_heading(text, "Component Under Test")
        if component_type:
            report.pass_(f"{label}: component type declared as {component_type}")
        else:
            report.error(f"{label}: component type not declared")

        component_dir = component_type_to_dir(component_type or "")
        primary_component = linked_path_containing(linked_files, component_dir) if component_dir else None
        if primary_component:
            report.pass_(f"{label}: primary component profile linked")
        else:
            report.error(f"{label}: primary component profile link missing")

        required_harness = [
            "strategies",
            "schedules",
            "universes",
            "portfolio-policies",
            "execution-models",
            "funding",
        ]
        missing_harness = [
            part for part in required_harness if not linked_path_containing(linked_files, part)
        ]
        if missing_harness:
            report.error(f"{label}: fixed harness links missing: {', '.join(missing_harness)}")
        else:
            report.pass_(f"{label}: fixed harness links resolve")

        if linked_path_containing(linked_files, "evaluations"):
            report.pass_(f"{label}: evaluation profile linked")
        else:
            report.warn(f"{label}: no evaluation profile linked")

        if extract_section(text, "Metrics"):
            report.pass_(f"{label}: metrics section present")
        else:
            report.error(f"{label}: metrics section missing")

        output_section = extract_section(text, "Output Location")
        if "data/stock/component-benchmarks/" in output_section:
            report.pass_(f"{label}: output location declared")
        else:
            report.error(f"{label}: output location missing or outside data/stock/component-benchmarks/")


def markdown_links(text: str) -> list[tuple[str, str]]:
    return re.findall(r"\[([^\]]+)\]\(([^)]+)\)", text)


def linked_path_containing(paths: list[Path], part: str) -> Path | None:
    for path in paths:
        if part in path.parts:
            return path
    return None


def component_type_to_dir(component_type: str) -> str | None:
    return {
        "selection-model": "selection-models",
        "portfolio-policy": "portfolio-policies",
        "execution-model": "execution-models",
        "universe": "universes",
        "schedule": "schedules",
        "funding-profile": "funding",
        "evaluation-window": "evaluations",
    }.get(component_type)


def validate_selection_policy_compat(
    report: Report, label: str, selection: Path, policy: Path
) -> None:
    selection_text = read(selection)
    policy_text = read(policy)
    selection_is_top_n = "target_count" in selection_text or "multiple target" in selection_text.lower()
    policy_is_single = "Single selected ticker" in policy_text
    policy_is_multi = "Multiple target-weight positions" in policy_text

    if policy_is_single and selection_is_top_n:
        report.error(f"{label}: single-position policy linked to multi-target selection model")
    elif policy_is_multi and not selection_is_top_n:
        report.error(f"{label}: multi-position policy linked to single-target selection model")
    else:
        report.pass_(f"{label}: selection model is compatible with portfolio policy")


def validate_policy_execution_compat(
    report: Report, label: str, policy: Path, execution: Path
) -> None:
    policy_text = read(policy)
    execution_text = read(execution)
    policy_mentions_settled = re.search(r"settled|settlement|proceeds", policy_text, re.I)
    execution_defines_settlement = "settlement_lag" in execution_text
    if policy_mentions_settled and not execution_defines_settlement:
        report.warn(f"{label}: policy mentions settlement but execution model has no settlement_lag")
    else:
        report.pass_(f"{label}: execution model is compatible with portfolio policy")


def title(text: str) -> str:
    match = re.search(r"^# (.+)$", text, re.M)
    return match.group(1) if match else ""


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


if __name__ == "__main__":
    raise SystemExit(main())
