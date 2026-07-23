#!/usr/bin/env python3
"""Behavioral tests for the fundamental-technical momentum selector."""

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "stages/selection-models/fundamental_technical_momentum.py"
SPEC = importlib.util.spec_from_file_location("fundamental_technical_momentum", MODULE_PATH)
selector = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = selector
SPEC.loader.exec_module(selector)


def eligible_row(ret_252, relative_volume):
    return {
        **{field: "true" for field in selector.BOOLEAN_FIELDS},
        "ret_252": str(ret_252),
        "relative_volume_50": str(relative_volume),
    }


class FundamentalTechnicalMomentumTest(unittest.TestCase):
    def test_requires_every_condition_and_ranks_deterministically(self):
        features = {
            "AAA": eligible_row(0.30, 1.6),
            "BBB": eligible_row(0.40, 1.7),
            "CCC": eligible_row(0.40, 2.0),
            "DDD": eligible_row(0.50, 2.0),
        }
        features["DDD"]["is_debt_lowers"] = "false"

        result = selector.select(
            as_of="2026-07-22",
            candidates=["AAA", "BBB", "CCC", "DDD"],
            features=features,
            target_count=2,
        )

        self.assertEqual(
            ["CCC", "BBB", "AAA"],
            [row["instrument_id"] for row in result.ranking],
        )
        self.assertEqual(
            ({"instrument_id": "CCC", "weight": 0.5}, {"instrument_id": "BBB", "weight": 0.5}),
            result.targets,
        )
        self.assertIn("failed:is_debt_lowers", result.eligibility["DDD"]["reasons"])

    def test_missing_evidence_is_reported_and_can_use_fallback(self):
        row = eligible_row(0.30, 1.6)
        row["is_eps_growing"] = ""

        result = selector.select(
            as_of="2026-07-22",
            candidates=["AAA"],
            features={"AAA": row},
            fallback_mode="fallback",
            fallback_ticker="BIL",
        )

        self.assertTrue(result.fallback_used)
        self.assertEqual(({"instrument_id": "BIL", "weight": 1.0},), result.targets)
        self.assertIn("missing:is_eps_growing", result.eligibility["AAA"]["reasons"])

    def test_rejects_invalid_configuration(self):
        with self.assertRaises(ValueError):
            selector.select(
                as_of="2026-07-22",
                candidates=[],
                features={},
                target_count=0,
            )

    def test_seven_condition_variant_does_not_require_high_volume(self):
        row = eligible_row(0.30, 1.1)
        row["is_high_relative_volume"] = "false"

        strict = selector.select(
            as_of="2026-07-22",
            candidates=["AAA"],
            features={"AAA": row},
        )
        seven = selector.select_without_high_relative_volume(
            as_of="2026-07-22",
            candidates=["AAA"],
            features={"AAA": row},
        )

        self.assertFalse(strict.targets)
        self.assertEqual(
            ({"instrument_id": "AAA", "weight": 1.0},),
            seven.targets,
        )


if __name__ == "__main__":
    unittest.main()
