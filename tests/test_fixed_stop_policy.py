#!/usr/bin/env python3
"""Behavioral tests for conservative fixed-stop fills."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/backtests/strategies/technical_resistance_runner.py"
SPEC = importlib.util.spec_from_file_location("technical_resistance_runner_stop", MODULE_PATH)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class FixedStopPolicyTest(unittest.TestCase):
    def test_untouched_stop_has_no_fill(self):
        self.assertIsNone(runner.fixed_stop_fill_price(101.0, 100.01, 100.0))

    def test_intraday_touch_fills_at_stop(self):
        self.assertEqual(runner.fixed_stop_fill_price(101.0, 99.0, 100.0), 100.0)

    def test_gap_through_fills_at_worse_open(self):
        self.assertEqual(runner.fixed_stop_fill_price(95.0, 94.0, 100.0), 95.0)

    def test_missing_bar_does_not_infer_fill(self):
        self.assertIsNone(runner.fixed_stop_fill_price(None, 99.0, 100.0))
        self.assertIsNone(runner.fixed_stop_fill_price(101.0, None, 100.0))


if __name__ == "__main__":
    unittest.main()
