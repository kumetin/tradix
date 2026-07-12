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
    def prediction(self) -> dict:
        return {
            "prediction_id": "2026-01-01|example|TEST",
            "evaluator_id": "example",
            "evaluation_date": "2026-01-01",
            "ticker": "TEST",
            "action": "buy",
        }

    def buy_signal(self) -> backtest.SetupSignal:
        return backtest.SetupSignal(
            evaluator_id="example",
            ticker="TEST",
            evaluation_date="2026-01-01",
            action="buy",
            setup_score=90.0,
            evidence_score=90.0,
            current_price=100.0,
            entry_price=100.0,
            buy_limit=98.0,
            stop_loss=95.0,
            take_profit=110.0,
        )

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

    def test_signal_eligibility_applies_action_setup_score_and_evidence_score(self) -> None:
        signal = backtest.SetupSignal(
            evaluator_id="example",
            ticker="TEST",
            evaluation_date="2026-01-01",
            action="buy",
            setup_score=79.0,
            evidence_score=85.0,
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
            min_setup_score=80.0,
            min_evidence_score=80.0,
        )

        self.assertFalse(backtest.signal_is_eligible(signal, config))
        self.assertTrue(backtest.signal_is_eligible(signal, replace(config, min_setup_score=70.0)))

    def test_signal_horizon_return_does_not_depend_on_signal_eligibility(self) -> None:
        signal = backtest.SetupSignal(
            evaluator_id="example",
            ticker="TEST",
            evaluation_date="2026-01-01",
            action="avoid",
            setup_score=20.0,
            evidence_score=20.0,
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

    def test_same_day_stop_and_take_profit_hit_uses_conservative_stop_first(self) -> None:
        signal = SimpleNamespace(
            take_profit=110.0,
            stop_loss=95.0,
        )
        future_rows = [
            {"date": "2026-01-02", "adj_high": "111", "adj_low": "94", "adj_close": "108"},
        ]

        outcome = backtest.measured_outcome(
            self.prediction(),
            signal,
            "close_entry",
            1,
            future_rows,
            100.0,
            "2026-01-01",
            [],
        )

        self.assertEqual(outcome["exit_reason"], "stop_loss")
        self.assertEqual(outcome["first_exit"], "stop_loss")
        self.assertTrue(outcome["hit_take_profit"])
        self.assertTrue(outcome["hit_stop_loss"])
        self.assertEqual(outcome["days_to_take_profit"], 1)
        self.assertEqual(outcome["days_to_stop_loss"], 1)

    def test_limit_entry_enters_when_adjusted_low_touches_buy_limit(self) -> None:
        rows = [
            {"date": "2026-01-01", "adj_close": "100", "adj_high": "101", "adj_low": "99"},
            {"date": "2026-01-02", "adj_close": "101", "adj_high": "102", "adj_low": "99"},
            {"date": "2026-01-05", "adj_close": "105", "adj_high": "106", "adj_low": "97.5"},
            {"date": "2026-01-06", "adj_close": "111", "adj_high": "112", "adj_low": "104"},
        ]

        outcome = backtest.limit_entry_outcome(
            self.prediction(),
            self.buy_signal(),
            rows,
            [],
            3,
            eligible=True,
        )

        self.assertTrue(outcome["entered"])
        self.assertEqual(outcome["entry_date"], "2026-01-05")
        self.assertEqual(outcome["entry_price"], 98.0)
        self.assertEqual(outcome["exit_reason"], "take_profit")
        self.assertEqual(outcome["exit_date"], "2026-01-06")
        self.assertAlmostEqual(outcome["realized_return"], 110.0 / 98.0 - 1.0)

    def test_limit_entry_remains_unentered_when_buy_limit_is_not_touched(self) -> None:
        rows = [
            {"date": "2026-01-01", "adj_close": "100", "adj_high": "101", "adj_low": "99"},
            {"date": "2026-01-02", "adj_close": "101", "adj_high": "102", "adj_low": "99"},
            {"date": "2026-01-05", "adj_close": "105", "adj_high": "106", "adj_low": "98.5"},
        ]

        outcome = backtest.limit_entry_outcome(
            self.prediction(),
            self.buy_signal(),
            rows,
            [],
            2,
            eligible=True,
        )

        self.assertFalse(outcome["entered"])
        self.assertEqual(outcome["entry_mode"], "limit_entry")
        self.assertEqual(outcome["realized_return"], "")

    def test_close_entry_uses_empty_outcome_when_signal_is_not_eligible(self) -> None:
        rows = [
            {"date": "2026-01-01", "adj_close": "100", "adj_high": "101", "adj_low": "99"},
            {"date": "2026-01-02", "adj_close": "105", "adj_high": "106", "adj_low": "104"},
        ]

        outcome = backtest.close_entry_outcome(
            self.prediction(),
            replace(self.buy_signal(), action="avoid"),
            rows,
            [],
            1,
            eligible=False,
        )

        self.assertFalse(outcome["entered"])
        self.assertEqual(outcome["entry_mode"], "close_entry")

    def test_benchmark_return_uses_last_available_date_on_or_before_signal_date(self) -> None:
        rows = [
            {"date": "2026-01-01", "adj_close": "100"},
            {"date": "2026-01-05", "adj_close": "102"},
            {"date": "2026-01-06", "adj_close": "104"},
        ]

        value = backtest.benchmark_return(rows, "2026-01-03", 1)

        self.assertAlmostEqual(value, 0.02)

    def test_build_outcomes_records_universe_equal_weight_from_all_signals(self) -> None:
        buy = self.buy_signal()
        avoid = backtest.SetupSignal(
            evaluator_id="example",
            ticker="WEAK",
            evaluation_date="2026-01-01",
            action="avoid",
            setup_score=10.0,
            evidence_score=20.0,
            current_price=50.0,
            entry_price=50.0,
            buy_limit=None,
            stop_loss=None,
            take_profit=None,
        )
        predictions = [
            backtest.prediction_row("2026-01-01|example|TEST", buy, {}),
            backtest.prediction_row("2026-01-01|example|WEAK", avoid, {}),
        ]
        rows_by_ticker = {
            "TEST": [
                {"date": "2026-01-01", "adj_close": "100", "adj_high": "101", "adj_low": "99"},
                {"date": "2026-01-02", "adj_close": "110", "adj_high": "111", "adj_low": "109"},
            ],
            "WEAK": [
                {"date": "2026-01-01", "adj_close": "50", "adj_high": "51", "adj_low": "49"},
                {"date": "2026-01-02", "adj_close": "45", "adj_high": "46", "adj_low": "44"},
            ],
        }
        config = backtest.BacktestConfig(
            tickers=["TEST", "WEAK"],
            start_date=dt.date(2026, 1, 1),
            end_date=dt.date(2026, 1, 31),
            frequency="daily",
            horizons=[1],
            benchmark_ticker="SPY",
            output_dir=Path("/tmp/setup-signal-backtest"),
        )

        outcomes = backtest.build_outcomes(
            predictions,
            {
                "2026-01-01|example|TEST": buy,
                "2026-01-01|example|WEAK": avoid,
            },
            rows_by_ticker,
            [],
            config,
        )

        close_outcomes = [row for row in outcomes if row["entry_mode"] == "close_entry"]
        self.assertEqual(len(close_outcomes), 2)
        for row in close_outcomes:
            self.assertAlmostEqual(row["universe_equal_weight_forward_return"], 0.0)

    def test_build_execution_report_contains_scenario_summary_insights_and_next_steps(self) -> None:
        adapter = SimpleNamespace(evaluator_id="example-evaluator")
        config = backtest.BacktestConfig(
            tickers=["TEST", "WEAK"],
            start_date=dt.date(2026, 1, 1),
            end_date=dt.date(2026, 1, 31),
            frequency="weekly",
            horizons=[5, 10],
            benchmark_ticker="SPY",
            output_dir=Path("/tmp/setup-signal-backtest"),
            min_setup_score=80.0,
            scenario_slug="Example Scenario",
            run_timestamp="20260711-143022Z",
            config_hash="abc12345",
        )
        run_config = backtest.run_config_row(adapter, config)
        predictions = [
            {"evaluation_date": "2026-01-02", "ticker": "TEST", "action": "buy"},
            {"evaluation_date": "2026-01-02", "ticker": "WEAK", "action": "avoid"},
        ]
        summaries = [
            {
                "evaluator_id": "example-evaluator",
                "entry_mode": "close_entry",
                "horizon_days": 5,
                "group_type": "action",
                "group": "buy",
                "count": 1,
                "entered_count": 1,
                "win_rate": 1.0,
                "average_realized_return": 0.04,
                "median_realized_return": 0.04,
                "average_horizon_return": 0.03,
                "average_max_favorable_excursion": 0.06,
                "average_max_adverse_excursion": -0.01,
                "take_profit_rate": 0.0,
                "stop_loss_rate": 0.0,
                "average_benchmark_forward_return": 0.01,
                "average_universe_equal_weight_forward_return": 0.0,
            },
            {
                "evaluator_id": "example-evaluator",
                "entry_mode": "limit_entry",
                "horizon_days": 5,
                "group_type": "action",
                "group": "buy",
                "count": 1,
                "entered_count": 0,
                "win_rate": "",
                "average_realized_return": "",
                "median_realized_return": "",
                "average_horizon_return": "",
                "average_max_favorable_excursion": "",
                "average_max_adverse_excursion": "",
                "take_profit_rate": "",
                "stop_loss_rate": "",
                "average_benchmark_forward_return": 0.01,
                "average_universe_equal_weight_forward_return": 0.0,
            },
        ]

        report = backtest.build_execution_report(adapter, config, run_config, predictions, [], summaries)

        self.assertIn("# Setup Signal Backtest Execution Report: example-evaluator", report)
        self.assertIn("## Scenario", report)
        self.assertIn("## Configuration", report)
        self.assertIn("| Scenario | example-scenario |", report)
        self.assertIn("| Config hash | abc12345 |", report)
        self.assertIn("## Headline Results", report)
        self.assertIn("## Notable Insights", report)
        self.assertIn("Best `buy` result was 4.00%", report)
        self.assertIn("## Ideas To Try Next", report)
        self.assertIn("`execution-report.md` records this human-readable run interpretation.", report)

    def test_build_predictions_html_embeds_setup_visualization_per_prediction(self) -> None:
        prediction = {
            "prediction_id": "2026-01-03|example|TEST",
            "evaluator_id": "example",
            "evaluation_date": "2026-01-03",
            "ticker": "TEST",
            "action": "buy",
            "setup_score": 90.0,
            "evidence_score": 85.0,
            "current_price": 102.0,
            "entry_price": 102.0,
            "buy_limit": 100.0,
            "stop_loss": 96.0,
            "take_profit": 112.0,
            "setup_status": "Ready / near buy zone",
        }
        feature_rows = {
            "TEST": [
                {"date": "2026-01-01", "adj_close": "98", "adj_high": "99", "adj_low": "97"},
                {"date": "2026-01-02", "adj_close": "100", "adj_high": "101", "adj_low": "99"},
                {"date": "2026-01-03", "adj_close": "102", "adj_high": "103", "adj_low": "101"},
            ]
        }

        page = backtest.build_predictions_html([prediction], feature_rows)

        self.assertIn("<title>Setup Signal Predictions</title>", page)
        self.assertIn("<svg", page)
        self.assertIn("TEST", page)
        self.assertIn("Ready / near buy zone", page)
        self.assertIn("$100.00", page)
        self.assertIn("$96.00", page)
        self.assertIn("$112.00", page)
        self.assertIn("buy limit", page)
        self.assertIn("stop loss", page)
        self.assertIn("take profit", page)

    def test_run_config_hash_is_stable_and_ignores_output_directory(self) -> None:
        adapter_id = "example-evaluator"
        config = backtest.BacktestConfig(
            tickers=["TEST", "WEAK"],
            start_date=dt.date(2026, 1, 1),
            end_date=dt.date(2026, 1, 31),
            frequency="weekly",
            horizons=[5, 10],
            benchmark_ticker="SPY",
            output_dir=Path("/tmp/one"),
            min_setup_score=80.0,
            scenario_slug="first-label",
        )

        same_run_hash = backtest.run_config_hash(
            adapter_id,
            replace(config, output_dir=Path("/tmp/two"), scenario_slug="second-label"),
        )
        changed_run_hash = backtest.run_config_hash(adapter_id, replace(config, min_setup_score=85.0))

        self.assertEqual(backtest.run_config_hash(adapter_id, config), same_run_hash)
        self.assertNotEqual(backtest.run_config_hash(adapter_id, config), changed_run_hash)

    def test_config_with_run_output_dir_uses_timestamp_evaluator_scenario_and_hash(self) -> None:
        config = backtest.BacktestConfig(
            tickers=["TEST"],
            start_date=dt.date(2026, 1, 1),
            end_date=dt.date(2026, 1, 31),
            frequency="weekly",
            horizons=[5],
            benchmark_ticker="SPY",
            output_dir=Path("/tmp/unused"),
            scenario_slug="My Smoke Run",
        )

        resolved = backtest.config_with_run_output_dir(
            "example-evaluator",
            config,
            Path("/tmp/root"),
            timestamp="20260711-143022Z",
        )

        self.assertEqual(resolved.scenario_slug, "my-smoke-run")
        self.assertEqual(resolved.run_timestamp, "20260711-143022Z")
        self.assertEqual(resolved.config_hash, backtest.run_config_hash("example-evaluator", config))
        self.assertEqual(
            resolved.output_dir.name,
            f"20260711-143022Z__example-evaluator__my-smoke-run__{resolved.config_hash}",
        )
        self.assertEqual(resolved.output_dir.parent, Path("/tmp/root"))


if __name__ == "__main__":
    unittest.main()
