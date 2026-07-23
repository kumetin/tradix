#!/usr/bin/env python3
"""Test deterministic lower-risk swing-entry construction and scoring.

Parameters:
    None; unittest discovers the test methods.
External sources:
    The local lower-risk evaluator module and synthetic in-memory market inputs.
Side effects:
    Dynamically imports the evaluator and emits unittest results; no files or
    external services are used.
Examples:
    Run this test module directly::

        python3 tests/test_lower_risk_swing_entry_evaluator.py

    Run the evaluator test class verbosely::

        python3 -m unittest -v tests.test_lower_risk_swing_entry_evaluator.LowerRiskSwingEntryEvaluatorTest
"""

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "stages/setup-evaluators/lower_risk_swing_entry.py"
SPEC = importlib.util.spec_from_file_location("lower_risk_swing_entry", MODULE_PATH)
lower_risk_swing_entry = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = lower_risk_swing_entry
SPEC.loader.exec_module(lower_risk_swing_entry)

ANALYST_DATA_TARGET_AND_COUNT = lower_risk_swing_entry.ANALYST_DATA_TARGET_AND_COUNT
ANALYST_STABLE = lower_risk_swing_entry.ANALYST_STABLE
EXTENSION_HIGH = lower_risk_swing_entry.EXTENSION_HIGH
INDICATORS_COMPLETE = lower_risk_swing_entry.INDICATORS_COMPLETE
INITIAL_INVALIDATION_ATR_MULTIPLE = lower_risk_swing_entry.INITIAL_INVALIDATION_ATR_MULTIPLE
LEVELS_OBJECTIVE = lower_risk_swing_entry.LEVELS_OBJECTIVE
LowerRiskSwingEntryEvaluator = lower_risk_swing_entry.LowerRiskSwingEntryEvaluator
LowerRiskSwingEntryInputs = lower_risk_swing_entry.LowerRiskSwingEntryInputs
PRICE_DATA_CURRENT = lower_risk_swing_entry.PRICE_DATA_CURRENT
RECENCY_STALE_OR_EVENT_GAP = lower_risk_swing_entry.RECENCY_STALE_OR_EVENT_GAP
STATUS_READY_NEAR_BUY_ZONE = lower_risk_swing_entry.STATUS_READY_NEAR_BUY_ZONE
STATUS_WATCH_BREAKOUT_RETEST = lower_risk_swing_entry.STATUS_WATCH_BREAKOUT_RETEST
SUPPORT_CONFLUENCE_WITHIN_3PCT = lower_risk_swing_entry.SUPPORT_CONFLUENCE_WITHIN_3PCT
SUPPORT_STRONG_WITHIN_3PCT = lower_risk_swing_entry.SUPPORT_STRONG_WITHIN_3PCT
TRADE_MATH_RECONCILES = lower_risk_swing_entry.TRADE_MATH_RECONCILES
TREND_CONSTRUCTIVE_ABOVE_RISING_AVERAGES = lower_risk_swing_entry.TREND_CONSTRUCTIVE_ABOVE_RISING_AVERAGES
average_true_range = lower_risk_swing_entry.average_true_range


class LowerRiskSwingEntryEvaluatorTest(unittest.TestCase):
    def test_evaluate_scores_and_formats_breakdowns(self) -> None:
        result = LowerRiskSwingEntryEvaluator.evaluate(
            LowerRiskSwingEntryInputs(
                current_price=100.0,
                buy_limit=98.5,
                reward_risk=2.6,
                support_quality=SUPPORT_CONFLUENCE_WITHIN_3PCT,
                trend_structure=TREND_CONSTRUCTIVE_ABOVE_RISING_AVERAGES,
                analyst_support=ANALYST_STABLE,
                extension_risk=EXTENSION_HIGH,
                price_data_quality=PRICE_DATA_CURRENT,
                support_resistance_quality=LEVELS_OBJECTIVE,
                indicator_quality=INDICATORS_COMPLETE,
                analyst_data_quality=ANALYST_DATA_TARGET_AND_COUNT,
                trade_math_quality=TRADE_MATH_RECONCILES,
                recency_gap_risk=RECENCY_STALE_OR_EVENT_GAP,
            )
        )

        self.assertEqual(result.setup_score, 84)
        self.assertEqual(result.setup_status, STATUS_READY_NEAR_BUY_ZONE)
        self.assertEqual(result.setup_score_breakdown_text(), "SS=84; EP=22; SQ=20; RR=17; TS=15; AS=7; ER=3")
        self.assertEqual(result.evidence_score, 82)
        self.assertEqual(result.evidence_score_breakdown_text(), "ES=82; PD=20; SR=15; MA=15; AD=12; TM=20; RG=0")

    def test_score_sorts_by_deterministic_setup_score(self) -> None:
        lower_score = LowerRiskSwingEntryInputs(
            current_price=100.0,
            buy_limit=97.0,
            reward_risk=2.0,
            support_quality=SUPPORT_STRONG_WITHIN_3PCT,
            trend_structure=TREND_CONSTRUCTIVE_ABOVE_RISING_AVERAGES,
            analyst_support=ANALYST_STABLE,
            extension_risk=EXTENSION_HIGH,
            price_data_quality=PRICE_DATA_CURRENT,
            support_resistance_quality=LEVELS_OBJECTIVE,
            indicator_quality=INDICATORS_COMPLETE,
            analyst_data_quality=ANALYST_DATA_TARGET_AND_COUNT,
            trade_math_quality=TRADE_MATH_RECONCILES,
            recency_gap_risk=RECENCY_STALE_OR_EVENT_GAP,
        )
        higher_score = LowerRiskSwingEntryInputs(
            current_price=100.0,
            buy_limit=98.5,
            reward_risk=2.6,
            support_quality=SUPPORT_CONFLUENCE_WITHIN_3PCT,
            trend_structure=TREND_CONSTRUCTIVE_ABOVE_RISING_AVERAGES,
            analyst_support=ANALYST_STABLE,
            extension_risk=EXTENSION_HIGH,
            price_data_quality=PRICE_DATA_CURRENT,
            support_resistance_quality=LEVELS_OBJECTIVE,
            indicator_quality=INDICATORS_COMPLETE,
            analyst_data_quality=ANALYST_DATA_TARGET_AND_COUNT,
            trade_math_quality=TRADE_MATH_RECONCILES,
            recency_gap_risk=RECENCY_STALE_OR_EVENT_GAP,
        )

        scored = LowerRiskSwingEntryEvaluator.score([lower_score, higher_score])

        self.assertEqual([item.setup_score for item in scored], [84, 71])

    def test_score_setups_keeps_setup_fields_with_scored_evaluation(self) -> None:
        first = LowerRiskSwingEntryEvaluator.construct_setup("LOW", self.synthetic_rows(high=130.0))
        second = LowerRiskSwingEntryEvaluator.construct_setup("HIGH", self.synthetic_rows(high=150.0))

        scored = LowerRiskSwingEntryEvaluator.score_setups([first, second])

        self.assertEqual(scored[0].setup.ticker, "HIGH")
        self.assertEqual(scored[1].setup.ticker, "LOW")

    def test_construct_setup_uses_rolling_high_resistance(self) -> None:
        setup = LowerRiskSwingEntryEvaluator.construct_setup("TEST", self.synthetic_rows(high=150.0))
        evaluation = LowerRiskSwingEntryEvaluator.evaluate(setup.inputs)

        self.assertEqual(setup.key_resistance, 150.0)
        self.assertGreater(setup.reward_risk, 1.8)
        self.assertEqual(evaluation.setup_status, STATUS_READY_NEAR_BUY_ZONE)

    def test_invalidation_is_support_minus_atr_buffer(self) -> None:
        rows = self.synthetic_rows(high=150.0)
        setup = LowerRiskSwingEntryEvaluator.construct_setup("TEST", rows)
        atr = average_true_range(rows, 14)

        self.assertAlmostEqual(
            setup.invalidation_level,
            setup.key_support - atr * INITIAL_INVALIDATION_ATR_MULTIPLE,
            places=6,
        )

    def test_buy_limit_offset_places_near_support_entry_below_support(self) -> None:
        rows = self.synthetic_rows(high=150.0)
        baseline = LowerRiskSwingEntryEvaluator.construct_setup("TEST", rows)
        offset = LowerRiskSwingEntryEvaluator.construct_setup(
            "TEST",
            rows,
            buy_limit_offset=0.02,
        )

        self.assertEqual(baseline.buy_limit, baseline.current_price)
        self.assertAlmostEqual(offset.buy_limit, offset.key_support * 0.98)

    def test_entry_score_threshold_changes_ready_classification(self) -> None:
        inputs = LowerRiskSwingEntryInputs(
            current_price=100.0,
            buy_limit=98.5,
            reward_risk=2.6,
            support_quality=SUPPORT_CONFLUENCE_WITHIN_3PCT,
            trend_structure=TREND_CONSTRUCTIVE_ABOVE_RISING_AVERAGES,
            analyst_support=ANALYST_STABLE,
            extension_risk=EXTENSION_HIGH,
            price_data_quality=PRICE_DATA_CURRENT,
            support_resistance_quality=LEVELS_OBJECTIVE,
            indicator_quality=INDICATORS_COMPLETE,
            analyst_data_quality=ANALYST_DATA_TARGET_AND_COUNT,
            trade_math_quality=TRADE_MATH_RECONCILES,
            recency_gap_risk=RECENCY_STALE_OR_EVENT_GAP,
        )

        self.assertEqual(
            LowerRiskSwingEntryEvaluator.evaluate(inputs, 20).setup_status,
            STATUS_READY_NEAR_BUY_ZONE,
        )
        self.assertEqual(
            LowerRiskSwingEntryEvaluator.evaluate(inputs, 22).setup_status,
            STATUS_READY_NEAR_BUY_ZONE,
        )
        self.assertEqual(
            LowerRiskSwingEntryEvaluator.evaluate(inputs, 23).setup_status,
            STATUS_WATCH_BREAKOUT_RETEST,
        )

    def synthetic_rows(self, high: float) -> list:
        rows = []
        for index in range(260):
            close = 100.0 + index * 0.1
            row_high = close + 0.5
            if index == 200:
                row_high = high
            rows.append(
                {
                    "date": "2026-%03d" % (index + 1),
                    "adj_close": str(close),
                    "adj_high": str(row_high),
                    "adj_low": str(close - 0.5),
                    "sma_20": str(close - 1.0),
                    "sma_50": str(close - 2.0),
                    "sma_150": str(close - 3.0),
                    "sma_200": str(close - 4.0),
                    "ret_21": "0.05",
                    "ret_63": "0.10",
                    "dd_252": "-0.05",
                    "high_252": str(high),
                }
            )
        return rows


if __name__ == "__main__":
    unittest.main()
