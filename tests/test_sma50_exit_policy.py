#!/usr/bin/env python3
"""Behavioral tests for daily SMA50 portfolio-policy signal timing."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/backtests/strategies/technical_resistance_runner.py"
SPEC = importlib.util.spec_from_file_location("technical_resistance_runner", MODULE_PATH)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class Sma50ExitPolicyTest(unittest.TestCase):
    def initial_state(self):
        return {
            "previous_close": None,
            "previous_sma50": None,
            "below_count": 0,
            "armed": False,
        }

    def test_close_strictly_below_same_day_sma50_signals(self):
        self.assertTrue(runner.sma50_below_exit_signal(99.99, 100.0))

    def test_equal_or_above_does_not_signal(self):
        self.assertFalse(runner.sma50_below_exit_signal(100.0, 100.0))
        self.assertFalse(runner.sma50_below_exit_signal(100.01, 100.0))

    def test_missing_close_or_sma50_does_not_fabricate_signal(self):
        self.assertFalse(runner.sma50_below_exit_signal(None, 100.0))
        self.assertFalse(runner.sma50_below_exit_signal(99.0, None))

    def test_after_close_signal_cannot_execute_same_session(self):
        self.assertFalse(
            runner.sma50_next_open_exit_due("2025-01-02", "2025-01-02")
        )

    def test_after_close_signal_executes_on_later_session(self):
        self.assertTrue(
            runner.sma50_next_open_exit_due("2025-01-02", "2025-01-03")
        )

    def test_no_signal_never_executes(self):
        self.assertFalse(runner.sma50_next_open_exit_due(None, "2025-01-03"))

    def test_cross_requires_prior_row_at_or_above(self):
        signal, state = runner.evaluate_sma50_exit(
            "cross", 101.0, 100.0, self.initial_state()
        )
        self.assertFalse(signal)
        signal, _ = runner.evaluate_sma50_exit("cross", 99.0, 100.0, state)
        self.assertTrue(signal)

    def test_two_close_confirmation_ignores_first_below_close(self):
        signal, state = runner.evaluate_sma50_exit(
            "confirmed_2", 99.0, 100.0, self.initial_state()
        )
        self.assertFalse(signal)
        signal, _ = runner.evaluate_sma50_exit("confirmed_2", 98.0, 100.0, state)
        self.assertTrue(signal)

    def test_one_percent_buffer_is_strict(self):
        signal, _ = runner.evaluate_sma50_exit(
            "buffer_1pct", 99.0, 100.0, self.initial_state()
        )
        self.assertFalse(signal)
        signal, _ = runner.evaluate_sma50_exit(
            "buffer_1pct", 98.99, 100.0, self.initial_state()
        )
        self.assertTrue(signal)


if __name__ == "__main__":
    unittest.main()
