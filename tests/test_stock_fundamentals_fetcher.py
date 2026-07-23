#!/usr/bin/env python3
"""Behavioral tests for SEC Company Facts normalization."""

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FETCHER_PATH = ROOT / "scripts/market-data-fetchers/fetch_stock_fundamentals.py"
SPEC = importlib.util.spec_from_file_location("fetch_stock_fundamentals", FETCHER_PATH)
fetcher = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = fetcher
SPEC.loader.exec_module(fetcher)


def fact(value, start, end, filed, unit="USD", form="10-Q", accession="001"):
    row = {
        "val": value,
        "end": end,
        "filed": filed,
        "form": form,
        "accn": accession,
    }
    if start:
        row["start"] = start
    return unit, row


def payload_with(concepts):
    facts = {"us-gaap": {}}
    for concept, entries in concepts.items():
        units = {}
        for unit, row in entries:
            units.setdefault(unit, []).append(row)
        facts["us-gaap"][concept] = {"units": units}
    return {"facts": facts}


class StockFundamentalsFetcherTest(unittest.TestCase):
    def test_normalizes_quarterly_contexts_and_excludes_ytd_values(self):
        payload = payload_with(
            {
                "EarningsPerShareDiluted": [
                    fact(1.25, "2024-01-01", "2024-03-31", "2024-05-02", "USD/shares"),
                    fact(2.75, "2024-01-01", "2024-06-30", "2024-08-02", "USD/shares"),
                ],
                "RevenueFromContractWithCustomerExcludingAssessedTax": [
                    fact(100, "2024-01-01", "2024-03-31", "2024-05-02"),
                    fact(220, "2024-01-01", "2024-06-30", "2024-08-02"),
                ],
                "NetIncomeLoss": [
                    fact(10, "2024-01-01", "2024-03-31", "2024-05-02"),
                ],
                "LongTermDebt": [
                    fact(50, None, "2024-03-31", "2024-05-02"),
                ],
            }
        )

        rows = fetcher.normalize_company_facts(
            "TEST", payload, "2024-01-01", "2024-12-31"
        )

        self.assertEqual(1, len(rows))
        self.assertEqual("2024-05-02", rows[0]["available_date"])
        self.assertEqual("1.25", rows[0]["diluted_eps"])
        self.assertEqual("100", rows[0]["revenue"])
        self.assertEqual("10", rows[0]["net_income"])
        self.assertEqual("50", rows[0]["total_debt"])
        self.assertEqual("", rows[0]["institutional_ownership_pct"])

    def test_keeps_restatement_as_a_later_point_in_time_version(self):
        payload = payload_with(
            {
                "NetIncomeLoss": [
                    fact(10, "2024-01-01", "2024-03-31", "2024-05-02", accession="001"),
                    fact(
                        12,
                        "2024-01-01",
                        "2024-03-31",
                        "2024-05-10",
                        form="10-Q/A",
                        accession="002",
                    ),
                ]
            }
        )

        rows = fetcher.normalize_company_facts(
            "TEST", payload, "2024-01-01", "2024-12-31"
        )

        self.assertEqual(["2024-05-02", "2024-05-10"], [row["available_date"] for row in rows])
        self.assertEqual(["10", "12"], [row["net_income"] for row in rows])

    def test_ticker_map_normalizes_class_share_separator(self):
        payload = {
            "fields": ["cik", "name", "ticker", "exchange"],
            "data": [[1067983, "Berkshire Hathaway", "BRK.B", "NYSE"]],
        }
        self.assertEqual("0001067983", fetcher.ticker_to_cik(payload, "BRK-B"))


if __name__ == "__main__":
    unittest.main()
