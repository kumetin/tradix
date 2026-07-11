#!/usr/bin/env python3
"""Tests for generic setup-evaluator backtest helpers."""

import datetime as dt
import importlib.util
import sys
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/backtests/setup_evaluator_backtest.py"
SPEC = importlib.util.spec_from_file_location("setup_evaluator_backtest", MODULE_PATH)
backtest = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = backtest
SPEC.loader.exec_module(backtest)


class SetupEvaluatorBacktestTest(unittest.TestCase):
    def test_select_evaluation_dates_uses_last_available_weekly_date(self) -> None:
        rows = [
            {"date": "2026-01-05"},
            {"date": "2026-01-06"},
            {"date": "2026-01-09"},
            {"date": "2026-01-12"},
        ]

        selected = backtest.select_evaluation_dates(
            [rows],
            dt.date(2026, 1, 1),
            dt.date(2026, 1, 31),
            "weekly",
        )

        self.assertEqual(selected, ["2026-01-09", "2026-01-12"])

    def test_rows_through_date_excludes_future_rows(self) -> None:
        rows = [
            {"date": "2026-01-05", "adj_close": "100"},
            {"date": "2026-01-06", "adj_close": "101"},
            {"date": "2026-01-07", "adj_close": "102"},
        ]

        point_in_time = backtest.rows_through_date(rows, "2026-01-06")

        self.assertEqual([row["date"] for row in point_in_time], ["2026-01-05", "2026-01-06"])

    def test_excursions_are_zero_when_price_never_moves_past_entry(self) -> None:
        self.assertEqual(backtest.favorable_excursion(100.0, 95.0), 0.0)
        self.assertEqual(backtest.adverse_excursion(100.0, 105.0), 0.0)
        self.assertAlmostEqual(backtest.favorable_excursion(100.0, 110.0), 0.1)
        self.assertAlmostEqual(backtest.adverse_excursion(100.0, 90.0), -0.1)

    def test_signal_eligibility_applies_action_score_and_confidence(self) -> None:
        signal = backtest.SetupSignal(
            evaluator_id="example",
            ticker="TEST",
            evaluation_date="2026-01-01",
            action="buy",
            score=79.0,
            confidence=85.0,
            current_price=100.0,
            entry_price=100.0,
            buy_limit=99.0,
            stop_loss=95.0,
            take_profit=110.0,
        )
        config = backtest.BacktestConfig(
            tickers=["TEST"],
            start_date=dt.date(2026, 1, 1),
            end_date=dt.date(2026, 1, 31),
            frequency="weekly",
            horizons=[5],
            benchmark_ticker="SPY",
            output_dir=Path("/tmp/setup-signal-backtest"),
            min_score=80.0,
            min_confidence=80.0,
        )

        self.assertFalse(backtest.signal_is_eligible(signal, config))
        self.assertTrue(backtest.signal_is_eligible(signal, replace(config, min_score=70.0)))

    def test_signal_horizon_return_does_not_depend_on_signal_eligibility(self) -> None:
        signal = backtest.SetupSignal(
            evaluator_id="example",
            ticker="TEST",
            evaluation_date="2026-01-01",
            action="avoid",
            score=20.0,
            confidence=20.0,
            current_price=100.0,
            entry_price=100.0,
            buy_limit=None,
            stop_loss=None,
            take_profit=None,
        )
        rows = [
            {"date": "2026-01-01", "adj_close": "100"},
            {"date": "2026-01-02", "adj_close": "105"},
        ]

        self.assertAlmostEqual(backtest.signal_horizon_return(signal, rows, 1), 0.05)

    def test_measured_outcome_uses_first_exit_for_realized_return(self) -> None:
        prediction = {
            "prediction_id": "2026-01-01|example|TEST",
            "evaluator_id": "example",
            "evaluation_date": "2026-01-01",
            "ticker": "TEST",
            "action": "buy",
        }
        signal = SimpleNamespace(
            take_profit=110.0,
            stop_loss=95.0,
        )
        future_rows = [
            {"date": "2026-01-02", "adj_high": "102", "adj_low": "94", "adj_close": "101"},
            {"date": "2026-01-03", "adj_high": "109", "adj_low": "100", "adj_close": "108"},
        ]

        outcome = backtest.measured_outcome(
            prediction,
            signal,
            "close_entry",
            2,
            future_rows,
            100.0,
            "2026-01-01",
            [],
        )

        self.assertEqual(outcome["exit_reason"], "stop_loss")
        self.assertEqual(outcome["exit_date"], "2026-01-02")
        self.assertEqual(outcome["exit_price"], 95.0)
        self.assertAlmostEqual(outcome["realized_return"], -0.05)
        self.assertAlmostEqual(outcome["horizon_return"], 0.08)


if __name__ == "__main__":
    unittest.main()
