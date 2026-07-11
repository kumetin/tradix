#!/usr/bin/env python3
"""Root backtest driver."""

from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent

SPEC_STRATEGY = "strategy"
SPEC_COMPONENT = "component"
BACKTEST_ISOLATED = "isolated component backtest"
BACKTEST_HARNESSED = "harnessed component backtest"


@dataclass(frozen=True)
class BacktestSpec:
    path: Path
    kind: str
    title: str
    component_type: Optional[str] = None
    backtest_type: Optional[str] = None


def main(argv: Optional[Sequence[str]] = None) -> int:
    args, driver_args = parse_args(argv)
    spec = resolve_backtest_spec(args.spec)
    validate_spec(spec)

    if args.validate_only:
        print(f"Validated {spec.kind} backtest: {rel(spec.path)}")
        return 0

    if spec.kind == SPEC_STRATEGY:
        return run_strategy_backtest(spec, driver_args)
    if spec.backtest_type == BACKTEST_HARNESSED:
        return run_harnessed_component_backtest(spec, driver_args)
    if spec.backtest_type == BACKTEST_ISOLATED:
        return run_isolated_component_backtest(spec, args.evaluator, driver_args)

    raise BacktestDriverError(f"Unsupported backtest spec: {rel(spec.path)}")


def parse_args(argv: Optional[Sequence[str]]) -> Tuple[argparse.Namespace, List[str]]:
    parser = argparse.ArgumentParser(
        description="Resolve, validate, and run a strategy or component backtest spec."
    )
    parser.add_argument("spec", type=Path)
    parser.add_argument("--evaluator")
    parser.add_argument("--validate-only", action="store_true")
    args, driver_args = parser.parse_known_args(argv)
    driver_args = list(driver_args)
    if driver_args and driver_args[0] == "--":
        driver_args = driver_args[1:]
    return args, driver_args


def resolve_backtest_spec(path: Path) -> BacktestSpec:
    resolved = path.resolve()
    if not resolved.exists():
        raise BacktestDriverError(f"Backtest spec does not exist: {path}")
    if ROOT not in resolved.parents:
        raise BacktestDriverError(f"Backtest spec must be inside this repository: {path}")

    rel_parts = resolved.relative_to(ROOT).parts
    text = read(resolved)
    title = markdown_title(text)
    if rel_parts[:2] == ("backtests", "strategies"):
        return BacktestSpec(path=resolved, kind=SPEC_STRATEGY, title=title)
    if rel_parts[:2] == ("backtests", "components"):
        return BacktestSpec(
            path=resolved,
            kind=SPEC_COMPONENT,
            title=title,
            component_type=inline_code_after_heading(text, "Component Under Test"),
            backtest_type=inline_code_after_heading(text, "Backtest Type"),
        )
    raise BacktestDriverError("Backtest spec must live under backtests/strategies/ or backtests/components/.")


def validate_spec(spec: BacktestSpec) -> None:
    text = read(spec.path)
    missing_links = missing_markdown_links(spec.path, text)
    if missing_links:
        raise BacktestDriverError(f"Missing linked files in {rel(spec.path)}: {', '.join(missing_links)}")

    if spec.kind == SPEC_STRATEGY:
        require_section(text, "Edge Being Tested", spec)
        require_section(text, "Benchmarks", spec)
        if "Strategy Flow:" not in text:
            raise BacktestDriverError(f"{rel(spec.path)} must reference a Strategy Flow")
        return

    if not spec.component_type:
        raise BacktestDriverError(f"{rel(spec.path)} must declare Component Under Test")
    if spec.backtest_type not in {BACKTEST_ISOLATED, BACKTEST_HARNESSED}:
        raise BacktestDriverError(f"{rel(spec.path)} must declare a valid Backtest Type")
    require_section(text, "Question", spec)
    require_section(text, "Metrics", spec)
    require_section(text, "Output Location", spec)
    if spec.backtest_type == BACKTEST_ISOLATED:
        require_section(text, "Direct Input/Output Contract", spec)
    else:
        require_section(text, "Fixed Harness", spec)


def run_strategy_backtest(spec: BacktestSpec, driver_args: Sequence[str]) -> int:
    raise BacktestDriverError(
        f"Strategy backtest driver selected for {rel(spec.path)}, but no portfolio-level engine is registered yet."
    )


def run_harnessed_component_backtest(spec: BacktestSpec, driver_args: Sequence[str]) -> int:
    raise BacktestDriverError(
        f"Harnessed component backtest driver selected for {rel(spec.path)}, but no portfolio-level engine is registered yet."
    )


def run_isolated_component_backtest(
    spec: BacktestSpec,
    evaluator: Optional[str],
    driver_args: Sequence[str],
) -> int:
    if spec.component_type != "setup-evaluator":
        raise BacktestDriverError(f"No isolated driver registered for component type {spec.component_type!r}.")
    if evaluator != "lower-risk-swing-entry":
        raise BacktestDriverError("Use --evaluator lower-risk-swing-entry for this isolated setup-evaluator backtest.")

    module = import_module_from_path(SCRIPT_DIR / "benchmark_lower_risk_swing_entry.py", "benchmark_lower_risk_swing_entry")
    return module.main(driver_args)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def markdown_title(text: str) -> str:
    match = re.search(r"^# (.+)$", text, re.M)
    return match.group(1) if match else ""


def section(text: str, heading: str) -> str:
    pattern = re.compile(r"^## " + re.escape(heading) + r"\s*$([\s\S]*?)(?=^## |\Z)", re.M)
    match = pattern.search(text)
    return match.group(1) if match else ""


def require_section(text: str, heading: str, spec: BacktestSpec) -> None:
    if not section(text, heading).strip():
        raise BacktestDriverError(f"{rel(spec.path)} missing required section: {heading}")


def inline_code_after_heading(text: str, heading: str) -> Optional[str]:
    match = re.search(r"`([^`]+)`", section(text, heading))
    return match.group(1) if match else None


def markdown_links(text: str) -> List[Tuple[str, str]]:
    return re.findall(r"\[([^\]]+)\]\(([^)]+)\)", text)


def missing_markdown_links(path: Path, text: str) -> List[str]:
    missing = []
    for _, href in markdown_links(text):
        if href.startswith("http"):
            continue
        href_path = href.split("#", 1)[0]
        if not href_path:
            continue
        target = (path.parent / href_path).resolve()
        if not target.exists():
            missing.append(href)
    return missing


def import_module_from_path(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


class BacktestDriverError(Exception):
    pass


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BacktestDriverError as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        raise SystemExit(2)
