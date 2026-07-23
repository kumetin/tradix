#!/usr/bin/env python3
"""Resolve, validate, and dispatch a repository backtest specification.

Parameters:
    ``spec`` is a strategy or component backtest Markdown path. ``--evaluator``
    can select a harness adapter, ``--validate-only`` suppresses execution, and
    arguments after ``--`` are forwarded to the selected driver.
External sources:
    Local backtest specifications, referenced stage descriptors/configuration
    profiles, and repository backtest driver modules.
Side effects:
    Validation reads files and prints a result. Execution imports and invokes a
    driver, which may write artifacts according to that driver's contract.
Examples:
    Validate a strategy specification without running it::

        python3 scripts/backtests/run_backtest.py backtests/strategies/momentum-rotation/tc-001-point-in-time-sp500.md --validate-only

    Run an isolated setup-evaluator specification and forward driver options::

        python3 scripts/backtests/run_backtest.py backtests/components/setup-evaluators/setup-evaluator-forward-outcome-benchmark.md --evaluator lower-risk-swing-entry -- --tickers NVDA --start-date 2025-01-01 --end-date 2025-12-31
"""

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
            component_type=(
                inline_code_after_heading(text, "Component Under Test")
                or inline_code_after_heading(text, "Applicable Component Type")
            ),
            backtest_type=inline_code_after_heading(text, "Backtest Type"),
        )
    raise BacktestDriverError("Backtest spec must live under backtests/strategies/ or backtests/components/.")


def validate_spec(spec: BacktestSpec) -> None:
    text = read(spec.path)
    missing_links = missing_markdown_links(spec.path, text)
    if missing_links:
        raise BacktestDriverError(f"Missing linked files in {rel(spec.path)}: {', '.join(missing_links)}")

    if spec.kind == SPEC_STRATEGY:
        require_section(text, "Configuration Intent", spec)
        require_section(text, "Benchmarks", spec)
        if not re.search(r"^Strategy:\s*\[[^]]+\]\([^)]+\)", text, re.MULTILINE):
            raise BacktestDriverError(f"{rel(spec.path)} must reference a Strategy")
        return

    if not spec.component_type:
        raise BacktestDriverError(
            f"{rel(spec.path)} must declare Component Under Test "
            "or Applicable Component Type"
        )
    if spec.backtest_type != BACKTEST_ISOLATED:
        raise BacktestDriverError(
            f"{rel(spec.path)} must declare {BACKTEST_ISOLATED!r}; "
            "strategy-dependent comparisons belong under backtests/strategies/"
        )
    require_section(text, "Question", spec)
    require_section(text, "Metrics", spec)
    require_section(text, "Output Location", spec)
    require_section(text, "Direct Input/Output Contract", spec)


def run_strategy_backtest(spec: BacktestSpec, driver_args: Sequence[str]) -> int:
    relative = spec.path.relative_to(ROOT)
    if relative == Path(
        "backtests/strategies/technical-resistance-runner/"
        "tc-001-random-50-universe-1-monthly.md"
    ):
        module = import_module_from_path(
            SCRIPT_DIR / "strategies/technical_resistance_runner.py",
            "technical_resistance_runner_strategy_backtest",
        )
        return module.main(driver_args)
    if relative == Path(
        "backtests/strategies/technical-resistance-runner/"
        "tc-002-random-50-universe-1-sma50-exit.md"
    ):
        module = import_module_from_path(
            SCRIPT_DIR / "strategies/technical_resistance_runner.py",
            "technical_resistance_runner_sma50_strategy_backtest",
        )
        defaults = [
            "--exit-variant",
            "full_at_5_21_sma50_exit",
            "--output",
            str(
                ROOT
                / "artifacts/stock/backtests/strategies/technical-resistance-runner/"
                "robustness/universe-1/full_at_5_21-sma50-exit"
            ),
        ]
        return module.main(defaults + list(driver_args))
    if relative == Path(
        "backtests/strategies/technical-resistance-runner/"
        "tc-003-pre-2014-sma50-robustness.md"
    ):
        module = import_module_from_path(
            SCRIPT_DIR / "strategies/technical_resistance_runner.py",
            "technical_resistance_runner_pre2014_strategy_backtest",
        )
        windows = (
            ("crisis", "2007-01-03", "2009-12-31"),
            ("recovery", "2010-01-04", "2013-12-31"),
        )
        for name, start, end in windows:
            for variant, output_name in (
                ("full_at_5_21", "baseline"),
                ("full_at_5_21_sma50_exit", "sma50"),
            ):
                status = module.main(
                    [
                        "--evaluation-start",
                        start,
                        "--evaluation-end",
                        end,
                        "--exit-variant",
                        variant,
                        "--output",
                        str(
                            ROOT
                            / "artifacts/stock/backtests/strategies/"
                            "technical-resistance-runner/untried-windows"
                            / name
                            / output_name
                        ),
                    ]
                    + list(driver_args)
                )
                if status:
                    return status
        return 0
    if relative == Path(
        "backtests/strategies/regime-gated-technical-resistance/"
        "tc-001-eight-dataset-robustness.md"
    ):
        module = import_module_from_path(
            SCRIPT_DIR / "strategies/technical_resistance_runner.py",
            "regime_gated_technical_resistance_strategy_backtest",
        )
        defaults = [
            "--exit-variant",
            "full_at_5_21",
            "--market-regime-sma-window",
            "200",
            "--stop-loss-return",
            "0.15",
            "--slippage-bps",
            "10",
            "--fee-per-order",
            "1",
            "--output",
            str(
                ROOT
                / "artifacts/stock/backtests/strategies/technical-resistance-runner/"
                "autonomous-costs/universe-1/market-sma-200-stop-15"
            ),
        ]
        return module.main(defaults + list(driver_args))
    raise BacktestDriverError(
        f"Strategy backtest driver selected for {rel(spec.path)}, but no portfolio-level engine is registered yet."
    )


def run_isolated_component_backtest(
    spec: BacktestSpec,
    evaluator: Optional[str],
    driver_args: Sequence[str],
) -> int:
    if spec.component_type == "selection-model":
        if spec.path.name == "classic-12-1-price-momentum.md":
            module = import_module_from_path(
                SCRIPT_DIR / "classic_12_1_momentum_validation.py",
                "classic_12_1_momentum_validation",
            )
            return module.main(driver_args)
        if spec.path.name == "continuous-fundamental-momentum-validation.md":
            module = import_module_from_path(
                SCRIPT_DIR / "continuous_fundamental_momentum_validation.py",
                "continuous_fundamental_momentum_validation",
            )
            return module.main(driver_args)
        if spec.path.name == "fundamental-technical-seven-condition-validation.md":
            module = import_module_from_path(
                SCRIPT_DIR / "seven_condition_selection_validation.py",
                "fundamental_technical_seven_condition_validation",
            )
            return module.main(driver_args)
        if spec.path.name == "high-relative-volume-matched-ablation.md":
            module = import_module_from_path(
                SCRIPT_DIR / "high_relative_volume_matched_ablation.py",
                "high_relative_volume_matched_ablation",
            )
            return module.main(driver_args)
        if spec.path.name == "fundamental-technical-condition-count.md":
            module = import_module_from_path(
                SCRIPT_DIR / "selection_condition_count_benchmark.py",
                "fundamental_technical_condition_count_benchmark",
            )
            return module.main(driver_args)
        if spec.path.name != "fundamental-technical-momentum.md":
            raise BacktestDriverError(
                f"No isolated driver registered for selection model {spec.path.stem!r}."
            )
        module = import_module_from_path(
            SCRIPT_DIR / "selection_model_forward_outcome_benchmark.py",
            "fundamental_technical_momentum_selection_model_benchmark",
        )
        return module.main(driver_args)
    if spec.component_type == "portfolio-policy":
        if spec.path.name != "partial-profit-breakeven-time-exit.md":
            raise BacktestDriverError(
                f"No isolated driver registered for portfolio policy {spec.path.stem!r}."
            )
        module = import_module_from_path(
            SCRIPT_DIR / "portfolio_policy_exit_benchmark.py",
            "partial_profit_breakeven_time_exit_policy_benchmark",
        )
        return module.main(driver_args)
    if spec.component_type != "setup-evaluator":
        raise BacktestDriverError(f"No isolated driver registered for component type {spec.component_type!r}.")
    if evaluator != "lower-risk-swing-entry":
        raise BacktestDriverError("Use --evaluator lower-risk-swing-entry for this isolated setup-evaluator backtest.")

    module = import_module_from_path(
        SCRIPT_DIR / "setup_evaluator_adapters/lower_risk_swing_entry.py",
        "lower_risk_swing_entry_setup_evaluator_adapter",
    )
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
