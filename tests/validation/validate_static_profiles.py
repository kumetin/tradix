#!/usr/bin/env python3
"""Validate stage descriptors, configuration profiles, and scenario bindings.

Parameters:
    None; repository roots and expected definition locations are derived from
    this file's path.
External sources:
    Local stage descriptors, configuration profiles, backtest specifications,
    and validation contracts documented in
    ``tests/validation/static-profiles.md``.
Side effects:
    Reads repository files, writes a pass/warn/fail report to stdout, and exits
    nonzero when validation errors exist. It does not modify repository
    definitions.
Examples:
    Run the validator from the repository root::

        python3 tests/validation/validate_static_profiles.py

    Capture its report while preserving the exit status::

        python3 tests/validation/validate_static_profiles.py > /tmp/profile-validation.txt

This is intentionally lightweight: it checks the contracts documented in
``tests/validation/static-profiles.md`` without requiring a full backtest engine.
"""

from __future__ import annotations

import datetime as dt
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

RECOGNIZED_TRIGGER_FREQUENCIES = {"daily", "weekly", "monthly", "quarterly"}

OPERATION_LINK_RULES = {
    "trigger": (r"\btriggers?\b", "OPERATIONS.md#trigger"),
    "universe": (
        r"\b(?:universe resolution|universe models?|static universes?)\b",
        "OPERATIONS.md#universe-resolution-and-universe-models",
    ),
    "market data": (
        r"\b(?:market-data resolution|market data(?: services?| providers?)?)\b",
        "OPERATIONS.md#market-data-resolution",
    ),
    "selection": (
        r"\b(?:selection models?|selection)\b",
        "OPERATIONS.md#selection-and-selection-models",
    ),
    "setup evaluator": (r"\bsetup evaluators?\b", "OPERATIONS.md#setup-evaluators"),
    "portfolio": (
        r"\b(?:portfolio transitions?|portfolio polic(?:y|ies))\b",
        "OPERATIONS.md#portfolio-transitions-and-portfolio-policies",
    ),
    "execution": (
        r"\b(?:execution models?|execution)\b",
        "OPERATIONS.md#execution-and-execution-models",
    ),
    "funding": (r"\b(?:funding profiles?|funding)\b", "OPERATIONS.md#funding-profiles"),
    "evaluation": (
        r"\b(?:evaluation plans?|evaluation)\b",
        "OPERATIONS.md#evaluation-plans",
    ),
}


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
    validate_triggers(report)
    validate_evaluations(report)
    validate_terminology(report)
    validate_research_boundaries(report)
    validate_setup_evaluator_descriptors(report)
    validate_strategy_backtests(report)
    validate_component_backtests(report)
    validate_operation_links(report)
    report.print()
    return 1 if report.errors else 0


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def configuration_profile_files(directory: str) -> list[Path]:
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


def extract_inline_codes_after_heading(text: str, heading: str) -> list[str]:
    return re.findall(r"`([^`]+)`", extract_section(text, heading))


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
    for path in configuration_profile_files("configuration/universes"):
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

        if fallback and fallback not in tickers:
            report.error(f"{label}: optional fallback ticker is not in universe")
        elif fallback:
            report.warn(f"{label}: fallback is deprecated; configure it on the selection model")

        missing = sorted(ticker for ticker in tickers if ticker not in symbols_available)
        if missing:
            report.error(f"{label}: tickers missing from local daily price dataset: {', '.join(missing)}")
        else:
            report.pass_(f"{label}: all tickers exist in local daily price dataset")


def available_price_symbols() -> set[str]:
    base = ROOT / "data/stock/prices/daily"
    return {path.stem for path in base.glob("*/*.csv")}


def validate_operation_links(report: Report) -> None:
    missing: list[str] = []
    operations_page = ROOT / "stages/OPERATIONS.md"
    excluded_roots = {"artifacts", "data"}
    for path in sorted(ROOT.rglob("*.md")):
        relative = path.relative_to(ROOT)
        if path == operations_page or relative.parts[0] in excluded_roots:
            continue
        text = read(path)
        visible_text = re.sub(r"```[\s\S]*?```", "", text)
        visible_text = re.sub(r"`[^`]*`", "", visible_text)
        visible_text = re.sub(r"\[([^]]*)\]\([^)]+\)", r"\1", visible_text)
        for concept, (pattern, required_target) in OPERATION_LINK_RULES.items():
            if re.search(pattern, visible_text, re.I) and required_target not in text:
                missing.append(f"{rel(path)} ({concept})")

    if missing:
        report.error(
            "operation-reference links missing: " + ", ".join(missing)
        )
    else:
        report.pass_("Markdown operation mentions link to canonical responsibilities")


def validate_funding(report: Report) -> None:
    for path in configuration_profile_files("configuration/funding"):
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


def validate_triggers(report: Report) -> None:
    for path in configuration_profile_files("configuration/triggers"):
        text = read(path)
        label = rel(path)
        value = extract_table_value(text, "trigger_frequency")
        frequency = (value or "").lower()
        if frequency in RECOGNIZED_TRIGGER_FREQUENCIES:
            report.pass_(f"{label}: recognized trigger_frequency {value}")
        else:
            report.error(f"{label}: unrecognized trigger_frequency {value!r}")

        if re.search(r"data available before|signal cutoff|known before", text, re.I):
            report.pass_(f"{label}: signal cutoff language present")
        else:
            report.warn(f"{label}: signal cutoff language not found")


def validate_evaluations(report: Report) -> None:
    for path in sorted((ROOT / "configuration/evaluations").glob("*/*.md")):
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
            report.warn(f"{label}: warm-up exclusion not mentioned in evaluation plan")

        split_method = extract_table_value(text, "split_method") or ""
        if re.search(r"locked|holdout", split_method, re.I):
            if re.search(r"locked|holdout", text, re.I):
                report.pass_(f"{label}: holdout labeling mentioned")
            else:
                report.warn(f"{label}: holdout split lacks explicit holdout labeling")
        else:
            report.pass_(f"{label}: no locked holdout configured")


def validate_strategy_backtests(report: Report) -> None:
    for path in sorted((ROOT / "backtests/strategies").glob("*/*.md")):
        text = read(path)
        label = rel(path)
        links = markdown_links(text)
        missing_links = []
        linked_files = []
        for _, href in links:
            if href.startswith("http"):
                continue
            target = (path.parent / href.split("#", 1)[0]).resolve()
            linked_files.append(target)
            if not target.exists():
                missing_links.append(href)
        if missing_links:
            report.error(f"{label}: missing linked files: {', '.join(missing_links)}")
        else:
            report.pass_(f"{label}: linked scenario bindings resolve")

        if extract_section(text, "Configuration Intent"):
            report.pass_(f"{label}: configuration intent declared")
        else:
            report.error(f"{label}: configuration intent missing")

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


def validate_terminology(report: Report) -> None:
    ambiguous_patterns = (
        r"\bcomponent profiles?\b",
        r"\bstage profiles?\b",
        r"\bselection-model profiles?\b",
        r"\bsetup-evaluator profiles?\b",
        r"\bportfolio-policy profiles?\b",
        r"\bexecution-model profiles?\b",
        r"\bevaluation profiles?\b",
        r"\brun profiles?\b",
        r"\brunner profiles?\b",
    )
    roots = (
        ROOT / "README.md",
        ROOT / "AGENTS.md",
        ROOT / "stages",
        ROOT / "strategies",
        ROOT / "backtests",
        ROOT / "configuration",
        ROOT / "experiments",
        ROOT / "scripts",
        ROOT / "tests",
    )
    paths = []
    for root in roots:
        if root.is_file():
            paths.append(root)
        else:
            paths.extend(root.rglob("*.md"))

    violations = []
    for path in sorted(set(paths)):
        if "archive" in path.parts:
            continue
        text = read(path)
        matches = [
            pattern
            for pattern in ambiguous_patterns
            if re.search(pattern, text, re.I)
        ]
        if matches:
            violations.append(rel(path))

    if violations:
        report.error(
            "ambiguous descriptor/profile terminology found: "
            + ", ".join(violations)
        )
    else:
        report.pass_(
            "terminology distinguishes stage descriptors, configuration "
            "profiles, stage instances, scenarios, and run configurations"
        )


def validate_research_boundaries(report: Report) -> None:
    forbidden_strategy_headings = {
        "Research Status",
        "Run Index",
        "Artifact Runs",
        "Results",
        "Findings",
        "Decision",
    }
    forbidden_scenario_headings = {
        "Experiment Status",
        "Status",
        "Hypothesis",
        "Thesis Claim Under Test",
        "Success Criteria",
        "Run Index",
        "Artifact Runs",
        "Results",
        "Findings",
        "Decision",
        "Evidence Against the Claim",
    }

    checks = (
        ("strategies", sorted((ROOT / "strategies").glob("*.md")), forbidden_strategy_headings),
        (
            "strategy backtests",
            sorted((ROOT / "backtests/strategies").glob("*/*.md")),
            forbidden_scenario_headings,
        ),
    )
    for group, paths, forbidden in checks:
        violations = []
        for path in paths:
            headings = set(re.findall(r"^#{2,3} (.+?)\s*$", read(path), re.M))
            present = sorted(headings & forbidden)
            if present:
                violations.append(f"{rel(path)} ({', '.join(present)})")
        if violations:
            report.error(f"{group}: research-owned headings found: {'; '.join(violations)}")
        else:
            report.pass_(f"{group}: research lifecycle content stays in experiments")


def validate_setup_evaluator_descriptors(report: Report) -> None:
    required_sections = (
        "ID",
        "Stage Type",
        "Purpose",
        "Input Contract",
        "Output Contract",
        "Behavior",
        "Parameters",
        "Data Requirements",
        "Point-in-Time Rules",
        "Failure Behavior",
        "Benchmark Contract",
        "Implementation",
    )
    base = ROOT / "stages/setup-evaluators"
    paths = sorted(
        path
        for path in base.glob("*.md")
        if path.name != "README.md"
    )
    for path in paths:
        text = read(path)
        label = rel(path)
        missing = [
            heading
            for heading in required_sections
            if not extract_section(text, heading)
        ]
        if missing:
            report.error(
                f"{label}: setup-evaluator descriptor sections missing: "
                f"{', '.join(missing)}"
            )
        else:
            report.pass_(f"{label}: setup-evaluator descriptor schema complete")

        if re.search(r"^## (?:Output Format|Human Review Inputs|Role)$", text, re.M):
            report.error(f"{label}: consumer presentation content belongs outside stages")
        else:
            report.pass_(f"{label}: presentation concerns delegated to consumers")


def validate_component_backtests(report: Report) -> None:
    base = ROOT / "backtests/components"
    if not base.exists():
        report.warn("backtests/components: directory does not exist")
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
            target = (path.parent / href.split("#", 1)[0]).resolve()
            linked_files.append(target)
            if not target.exists():
                missing_links.append(href)
        if missing_links:
            report.error(f"{label}: missing linked files: {', '.join(missing_links)}")
        else:
            report.pass_(f"{label}: linked component bindings resolve")

        binding_mode = "descriptor"
        component_type = extract_inline_code_after_heading(text, "Component Under Test")
        if not component_type:
            component_type = extract_inline_code_after_heading(
                text, "Applicable Component Type"
            )
            binding_mode = "type"
        if component_type:
            report.pass_(f"{label}: component type declared as {component_type}")
        else:
            report.error(f"{label}: component type not declared")

        component_dir = component_type_to_dir(component_type or "")
        primary_root = ROOT / component_dir if component_dir else None
        primary_descriptor = (
            next((linked for linked in linked_files if primary_root in linked.parents), None)
            if primary_root
            else None
        )
        if binding_mode == "type" and component_type:
            report.pass_(f"{label}: concrete stage descriptor delegated to experiment")
        elif primary_descriptor:
            report.pass_(f"{label}: primary stage descriptor linked")
        else:
            report.error(f"{label}: primary stage descriptor link missing")

        backtest_type_values = extract_inline_codes_after_heading(text, "Backtest Type")
        backtest_type = backtest_type_values[0] if backtest_type_values else ""
        if backtest_type == "isolated component backtest":
            report.pass_(f"{label}: backtest type declared as {backtest_type}")
        else:
            report.error(
                f"{label}: backtest type must be isolated component backtest; "
                "strategy-dependent tests belong under backtests/strategies"
            )

        if extract_section(text, "Direct Input/Output Contract"):
            report.pass_(f"{label}: direct input/output contract present")
        else:
            report.error(f"{label}: isolated component backtest missing direct input/output contract")

        if linked_path_containing(linked_files, "evaluations"):
            report.pass_(f"{label}: evaluation plan linked")
        elif binding_mode == "type":
            report.pass_(f"{label}: concrete evaluation plan delegated to experiment")
        else:
            report.warn(f"{label}: no evaluation plan linked")

        if extract_section(text, "Metrics"):
            report.pass_(f"{label}: metrics section present")
        else:
            report.error(f"{label}: metrics section missing")

        output_section = extract_section(text, "Output Location")
        if "artifacts/stock/backtests/components/" in output_section:
            report.pass_(f"{label}: output location declared")
        else:
            report.error(f"{label}: output location missing or outside artifacts/stock/backtests/components/")


def markdown_links(text: str) -> list[tuple[str, str]]:
    return re.findall(r"\[([^\]]+)\]\(([^)]+)\)", text)


def linked_path_containing(paths: list[Path], part: str) -> Path | None:
    for path in paths:
        if part in path.parts:
            return path
    return None


def component_type_to_dir(component_type: str) -> str | None:
    return {
        "selection-model": "stages/selection-models",
        "portfolio-policy": "stages/portfolio-policies",
        "execution-model": "stages/execution-models",
        "universe": "configuration/universes",
        "trigger": "configuration/triggers",
        "funding-profile": "configuration/funding",
        "evaluation-window": "configuration/evaluations",
        "setup-evaluator": "stages/setup-evaluators",
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
