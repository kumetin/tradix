#!/usr/bin/env python3
"""Tests for the lower-risk swing-entry setup backtest adapter."""

import importlib.util
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/backtests/setup_evaluator_adapters/lower_risk_swing_entry.py"
SPEC = importlib.util.spec_from_file_location("lower_risk_swing_entry_setup_evaluator_adapter", MODULE_PATH)
benchmark = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = benchmark
SPEC.loader.exec_module(benchmark)

lower_risk = benchmark.lower_risk_swing_entry


class LowerRiskSwingEntryBacktestAdapterTest(unittest.TestCase):
    def test_statuses_map_to_normalized_actions(self) -> None:
        self.assertEqual(
            benchmark.action_from_status(lower_risk.STATUS_READY_NEAR_BUY_ZONE),
            benchmark.ACTION_BUY,
        )
        self.assertEqual(
            benchmark.action_from_status(lower_risk.STATUS_WAIT_FOR_PULLBACK),
            benchmark.ACTION_WAIT,
        )
        self.assertEqual(
            benchmark.action_from_status(lower_risk.STATUS_WATCH_BREAKOUT_RETEST),
            benchmark.ACTION_WAIT,
        )
        self.assertEqual(
            benchmark.action_from_status(lower_risk.STATUS_TOO_EXTENDED),
            benchmark.ACTION_AVOID,
        )
        self.assertEqual(
            benchmark.action_from_status(lower_risk.STATUS_WEAK_ANALYST_SUPPORT),
            benchmark.ACTION_AVOID,
        )
        self.assertEqual(
            benchmark.action_from_status(lower_risk.STATUS_AVOID_FOR_NOW),
            benchmark.ACTION_AVOID,
        )

    def test_to_signal_preserves_trade_plan_and_score_metadata(self) -> None:
        setup = SimpleNamespace(
            ticker="TEST",
            latest_date="2026-01-02",
            current_price=100.0,
            buy_limit=99.0,
            invalidation_level=95.0,
            take_profit=112.0,
            setup_type="Pullback at 20-EMA",
            key_support=98.5,
            key_resistance=112.0,
            trailing_stop_amount=5.0,
            trailing_stop_pct=0.05,
            reward_risk=2.6,
        )
        evaluation = SimpleNamespace(
            setup_status=lower_risk.STATUS_READY_NEAR_BUY_ZONE,
            setup_score=84,
            evidence_score=88,
            setup_score_breakdown={"EP": 22, "SQ": 15, "RR": 17, "TS": 15, "AS": 7, "ER": 8},
            evidence_score_breakdown={"PD": 20, "SR": 15, "MA": 15, "AD": 8, "TM": 20, "RG": 10},
        )

        signal = benchmark.LowerRiskSwingEntryAdapter().to_signal(
            SimpleNamespace(setup=setup, evaluation=evaluation)
        )

        self.assertEqual(signal.evaluator_id, "lower-risk-swing-entry")
        self.assertEqual(signal.action, benchmark.ACTION_BUY)
        self.assertEqual(signal.setup_score, 84.0)
        self.assertEqual(signal.evidence_score, 88.0)
        self.assertEqual(signal.entry_price, 100.0)
        self.assertEqual(signal.buy_limit, 99.0)
        self.assertEqual(signal.stop_loss, 95.0)
        self.assertEqual(signal.take_profit, 112.0)
        self.assertEqual(signal.metadata["stop_model"], "current")
        self.assertEqual(signal.metadata["original_stop_loss"], 95.0)
        self.assertEqual(signal.metadata["setup_status"], lower_risk.STATUS_READY_NEAR_BUY_ZONE)
        self.assertEqual(signal.metadata["setup_score_breakdown"]["RR"], 17)
        self.assertEqual(signal.metadata["evidence_score_breakdown"]["TM"], 20)

    def test_to_signal_applies_wider_risk_stop_model(self) -> None:
        setup = SimpleNamespace(
            ticker="TEST",
            latest_date="2026-01-02",
            current_price=100.0,
            buy_limit=99.0,
            invalidation_level=95.0,
            take_profit=112.0,
            setup_type="Pullback at 20-EMA",
            key_support=98.5,
            key_resistance=112.0,
            trailing_stop_amount=5.0,
            trailing_stop_pct=0.05,
            reward_risk=2.6,
        )
        evaluation = SimpleNamespace(
            setup_status=lower_risk.STATUS_READY_NEAR_BUY_ZONE,
            setup_score=84,
            evidence_score=88,
            setup_score_breakdown={"EP": 22, "SQ": 15, "RR": 17, "TS": 15, "AS": 7, "ER": 8},
            evidence_score_breakdown={"PD": 20, "SR": 15, "MA": 15, "AD": 8, "TM": 20, "RG": 10},
        )

        signal = benchmark.LowerRiskSwingEntryAdapter(stop_model="risk-1.5").to_signal(
            SimpleNamespace(setup=setup, evaluation=evaluation)
        )

        self.assertEqual(signal.stop_loss, 93.0)
        self.assertEqual(signal.metadata["original_stop_loss"], 95.0)
        self.assertEqual(signal.metadata["stop_model"], "risk-1.5")

    def test_extra_prediction_row_flattens_evaluator_breakdowns(self) -> None:
        adapter = benchmark.LowerRiskSwingEntryAdapter()
        signal = SimpleNamespace(
            metadata={
                "setup_status": lower_risk.STATUS_READY_NEAR_BUY_ZONE,
                "stop_model": "current",
                "original_stop_loss": 95.0,
                "setup_type": "Pullback at 50-SMA",
                "key_support": 98.0,
                "key_resistance": 115.0,
                "trailing_stop_amount": 5.0,
                "trailing_stop_pct": 0.05,
                "reward_risk": 3.1,
                "setup_score_breakdown": {"EP": 25, "SQ": 20, "RR": 20, "TS": 15, "AS": 0, "ER": 10},
                "evidence_score_breakdown": {"PD": 20, "SR": 15, "MA": 15, "AD": 0, "TM": 20, "RG": 10},
            }
        )

        row = adapter.extra_prediction_row(signal)

        self.assertEqual(row["setup_status"], lower_risk.STATUS_READY_NEAR_BUY_ZONE)
        self.assertEqual(row["stop_model"], "current")
        self.assertEqual(row["original_stop_loss"], 95.0)
        self.assertEqual(row["setup_type"], "Pullback at 50-SMA")
        self.assertEqual(row["setup_score_ep"], 25)
        self.assertEqual(row["setup_score_as"], 0)
        self.assertEqual(row["evidence_score_ad"], 0)
        self.assertEqual(row["evidence_score_rg"], 10)


if __name__ == "__main__":
    unittest.main()
