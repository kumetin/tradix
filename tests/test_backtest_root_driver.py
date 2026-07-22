#!/usr/bin/env python3
"""Test root backtest driver resolution and validation.

Parameters:
    None; unittest discovers the test methods.
External sources:
    The local root driver and repository backtest specification Markdown files.
Side effects:
    Reads specifications, dynamically imports the driver, and emits unittest
    results; it does not execute backtests or write artifacts.
Examples:
    Run this test module directly::

        python3 tests/test_backtest_root_driver.py

    Run the root-driver test class verbosely::

        python3 -m unittest -v tests.test_backtest_root_driver.BacktestRootDriverTest
"""

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/backtests/run_backtest.py"
SPEC = importlib.util.spec_from_file_location("run_backtest", MODULE_PATH)
run_backtest = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = run_backtest
SPEC.loader.exec_module(run_backtest)


class BacktestRootDriverTest(unittest.TestCase):
    def test_parse_args_keeps_driver_args_separate(self) -> None:
        args, driver_args = run_backtest.parse_args(
            [
                "backtests/components/setup-evaluators/setup-signal-backtest.md",
                "--evaluator",
                "lower-risk-swing-entry",
                "--validate-only",
                "--",
                "--tickers",
                "NVDA",
            ]
        )

        self.assertEqual(args.evaluator, "lower-risk-swing-entry")
        self.assertTrue(args.validate_only)
        self.assertEqual(driver_args, ["--tickers", "NVDA"])

    def test_resolves_strategy_backtest(self) -> None:
        spec = run_backtest.resolve_backtest_spec(
            ROOT / "backtests/strategies/momentum-rotation/tc-001-high-beta-with-soxl.md"
        )

        self.assertEqual(spec.kind, run_backtest.SPEC_STRATEGY)
        run_backtest.validate_spec(spec)

    def test_resolves_isolated_component_backtest(self) -> None:
        spec = run_backtest.resolve_backtest_spec(
            ROOT / "backtests/components/setup-evaluators/setup-signal-backtest.md"
        )

        self.assertEqual(spec.kind, run_backtest.SPEC_COMPONENT)
        self.assertEqual(spec.component_type, "setup-evaluator")
        self.assertEqual(spec.backtest_type, run_backtest.BACKTEST_ISOLATED)
        run_backtest.validate_spec(spec)

    def test_resolves_harnessed_component_backtest(self) -> None:
        spec = run_backtest.resolve_backtest_spec(
            ROOT / "backtests/components/selection-models/sma-drawdown-trailing-return.md"
        )

        self.assertEqual(spec.kind, run_backtest.SPEC_COMPONENT)
        self.assertEqual(spec.component_type, "selection-model")
        self.assertEqual(spec.backtest_type, run_backtest.BACKTEST_HARNESSED)
        run_backtest.validate_spec(spec)


if __name__ == "__main__":
    unittest.main()
