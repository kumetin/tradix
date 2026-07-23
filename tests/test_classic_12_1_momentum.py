#!/usr/bin/env python3
"""Behavioral tests for classic 12-1 momentum selection."""

import importlib.util
import math
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "stages/selection-models/classic_12_1_momentum.py"
SPEC = importlib.util.spec_from_file_location("classic_12_1_momentum", PATH)
model = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = model
SPEC.loader.exec_module(model)


class ClassicMomentumTest(unittest.TestCase):
    def test_ranking_percentiles_and_weights(self):
        result = model.select(
            as_of="2020-12-31",
            candidates=["LOW", "HIGH", "MID"],
            features={
                "LOW": {"ret_252_21": -0.1},
                "HIGH": {"ret_252_21": 0.4},
                "MID": {"ret_252_21": 0.2},
            },
            target_count=2,
        )
        self.assertEqual(
            ["HIGH", "MID", "LOW"],
            [row["instrument_id"] for row in result.ranking],
        )
        self.assertEqual([100, 50, 0], [row["rating"] for row in result.ranking])
        self.assertEqual(1.0, sum(row["weight"] for row in result.targets))

    def test_negative_values_remain_eligible_and_ties_are_stable(self):
        result = model.select(
            as_of="2020-12-31",
            candidates=["BBB", "AAA"],
            features={
                "BBB": {"ret_252_21": -0.2},
                "AAA": {"ret_252_21": -0.2},
            },
        )
        self.assertEqual(
            ["AAA", "BBB"], [row["instrument_id"] for row in result.ranking]
        )

    def test_missing_and_non_finite_values_are_excluded(self):
        result = model.select(
            as_of="2020-12-31",
            candidates=["MISSING", "INF", "ABSENT"],
            features={
                "MISSING": {"ret_252_21": ""},
                "INF": {"ret_252_21": math.inf},
            },
        )
        self.assertFalse(result.targets)
        self.assertIn(
            "missing_or_non_finite:ret_252_21",
            result.eligibility["INF"]["reasons"],
        )
        self.assertIn("missing:feature_row", result.eligibility["ABSENT"]["reasons"])

    def test_invalid_configuration_and_fallback(self):
        with self.assertRaises(ValueError):
            model.select(as_of="2020-12-31", candidates=[], features={}, target_count=0)
        result = model.select(
            as_of="2020-12-31",
            candidates=[],
            features={},
            fallback_mode="fallback",
            fallback_ticker="BIL",
        )
        self.assertTrue(result.fallback_used)
        self.assertEqual("BIL", result.targets[0]["instrument_id"])


if __name__ == "__main__":
    unittest.main()
