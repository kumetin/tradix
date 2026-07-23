#!/usr/bin/env python3
"""Behavioral tests for daily technical and fundamental enrichment."""

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/stock-data-enrichment/precompute_daily_stock_features.py"
SPEC = importlib.util.spec_from_file_location("precompute_daily_stock_features", MODULE_PATH)
features = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = features
SPEC.loader.exec_module(features)


def price_rows(count=260):
    return [
        {
            "symbol": "TEST",
            "date": "2024-{:02d}-{:02d}".format(1 + index // 28, 1 + index % 28),
            "bar_size": "1d",
            "open": str(100 + index),
            "high": str(101 + index),
            "low": str(99 + index),
            "close": str(100 + index),
            "adj_close": str(100 + index),
            "volume": "1000",
        }
        for index in range(count)
    ]


def fact(period, available, eps, revenue, income, debt, institutional):
    return {
        "symbol": "TEST",
        "fiscal_period_end": period,
        "available_date": available,
        "diluted_eps": str(eps),
        "revenue": str(revenue),
        "net_income": str(income),
        "total_debt": str(debt),
        "institutional_ownership_pct": str(institutional),
    }


class DailyStockFeaturesTest(unittest.TestCase):
    def test_fundamentals_are_blank_until_comparable_point_in_time_evidence_exists(self):
        facts = [
            fact("2022-03-31", "2022-05-01", 1, 100, 10, 100, 50),
            fact("2023-03-31", "2023-05-01", 2, 120, 18, 75, 54),
        ]
        rows = [
            dict(price_rows(1)[0], date="2023-04-30"),
            dict(price_rows(1)[0], date="2023-05-01"),
        ]

        result = features.feature_rows(rows, facts)

        self.assertEqual(result[0]["is_eps_growing"], "")
        self.assertEqual(result[1]["is_eps_growing"], "true")
        self.assertEqual(result[1]["is_profit_margins_increasing"], "true")
        self.assertEqual(result[1]["is_revenue_rises"], "true")
        self.assertEqual(result[1]["is_debt_lowers"], "true")
        self.assertEqual(result[1]["is_institutional_accumalation_rising"], "")

    def test_technical_boolean_fields_use_sma200_and_benchmark_return(self):
        rows = price_rows()
        benchmark = {row["date"]: 0.10 for row in rows}

        result = features.feature_rows(rows, benchmark_returns=benchmark)

        self.assertEqual(result[198]["is_above_moving_average"], "")
        self.assertEqual(result[199]["is_above_moving_average"], "true")
        self.assertEqual(result[252]["is_relative_strength_high"], "true")

    def test_institutional_snapshot_is_not_applied_before_fetch_date(self):
        rows = [
            dict(price_rows(1)[0], date="2026-07-22"),
            dict(price_rows(1)[0], date="2026-07-23"),
        ]
        institutions = [
            {
                "available_date": "2026-07-23",
                "net_reported_shares_change": "25",
            }
        ]

        result = features.feature_rows(rows, institutional_rows=institutions)

        self.assertEqual("", result[0]["is_institutional_accumalation_rising"])
        self.assertEqual("true", result[1]["is_institutional_accumalation_rising"])

    def test_high_relative_volume_uses_prior_rows_and_requires_up_close(self):
        rows = price_rows(52)
        rows[50]["volume"] = "1600"
        rows[51]["volume"] = "2000"
        rows[51]["adj_close"] = rows[50]["adj_close"]
        rows[51]["close"] = rows[50]["close"]

        result = features.feature_rows(rows)

        self.assertEqual("", result[49]["is_high_relative_volume"])
        self.assertEqual("1.6", result[50]["relative_volume_50"])
        self.assertEqual("true", result[50]["is_high_relative_volume"])
        self.assertEqual("false", result[51]["is_high_relative_volume"])


if __name__ == "__main__":
    unittest.main()
