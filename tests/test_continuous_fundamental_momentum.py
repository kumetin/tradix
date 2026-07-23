#!/usr/bin/env python3
"""Behavioral tests for continuous fundamental-momentum selection."""

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "stages/selection-models/continuous_fundamental_momentum.py"
SPEC = importlib.util.spec_from_file_location("continuous_fundamental_momentum", PATH)
model = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = model
SPEC.loader.exec_module(model)


def row(momentum, true_count=5, known_count=5):
    result = {"ret_252": str(momentum)}
    for index, field in enumerate(model.FUNDAMENTAL_FIELDS):
        result[field] = (
            "true" if index < true_count else "false"
        ) if index < known_count else ""
    return result


class ContinuousFundamentalMomentumTest(unittest.TestCase):
    def test_composite_balances_fundamentals_and_momentum(self):
        result = model.select(
            as_of="2026-01-16",
            candidates=["FAST", "QUALITY", "MIDDLE"],
            features={
                "FAST": row(0.50, true_count=0),
                "QUALITY": row(0.10, true_count=5),
                "MIDDLE": row(0.30, true_count=4),
            },
            target_count=2,
        )
        self.assertEqual(
            ["MIDDLE", "FAST", "QUALITY"],
            [item["instrument_id"] for item in result.ranking],
        )
        self.assertEqual(0.5, result.targets[0]["weight"])

    def test_requires_four_known_fundamentals(self):
        result = model.select(
            as_of="2026-01-16",
            candidates=["ENOUGH", "SPARSE"],
            features={
                "ENOUGH": row(0.20, true_count=3, known_count=4),
                "SPARSE": row(0.30, true_count=3, known_count=3),
            },
        )
        self.assertEqual(["ENOUGH"], [item["instrument_id"] for item in result.ranking])
        self.assertIn(
            "insufficient:fundamental_evidence",
            result.eligibility["SPARSE"]["reasons"],
        )

    def test_missing_momentum_is_excluded(self):
        features = {"AAA": row(0.20)}
        features["AAA"]["ret_252"] = ""
        result = model.select(
            as_of="2026-01-16", candidates=["AAA"], features=features
        )
        self.assertFalse(result.targets)
        self.assertIn("missing:ret_252", result.eligibility["AAA"]["reasons"])


if __name__ == "__main__":
    unittest.main()
