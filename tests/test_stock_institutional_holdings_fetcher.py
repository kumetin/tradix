#!/usr/bin/env python3
"""Tests for Nasdaq institutional-holdings normalization."""

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "scripts/market-data-fetchers/fetch_stock_institutional_holdings.py"
SPEC = importlib.util.spec_from_file_location("fetch_stock_institutional_holdings", PATH)
fetcher = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = fetcher
SPEC.loader.exec_module(fetcher)


class InstitutionalHoldingsFetcherTest(unittest.TestCase):
    def test_normalizes_complete_response_and_sums_reported_changes(self):
        payload = {
            "data": {
                "activePositions": {
                    "rows": [
                        {
                            "positions": "Total Institutional Shares",
                            "holders": "2",
                            "shares": "1,500",
                        }
                    ]
                },
                "holdingsTransactions": {
                    "totalRecords": "2",
                    "table": {
                        "rows": [
                            {
                                "date": "03/31/2026",
                                "sharesHeld": "1,000",
                                "sharesChange": "100",
                            },
                            {
                                "date": "12/31/2025",
                                "sharesHeld": "500",
                                "sharesChange": "-25",
                            },
                        ]
                    },
                },
            }
        }

        row = fetcher.normalize_payload(
            "TEST",
            "https://example.test",
            payload,
            "2026-07-23T10:00:00+00:00",
        )

        self.assertEqual("2026-03-31", row["report_period_end"])
        self.assertEqual("2026-07-23", row["available_date"])
        self.assertEqual("1500", row["total_institutional_shares_held"])
        self.assertEqual("75", row["net_reported_shares_change"])
        self.assertEqual("2", row["institutional_holders"])

    def test_rejects_truncated_transaction_table(self):
        payload = {
            "data": {
                "holdingsTransactions": {
                    "totalRecords": "2",
                    "table": {"rows": [{"date": "03/31/2026"}]},
                }
            }
        }
        with self.assertRaisesRegex(RuntimeError, "Incomplete Nasdaq response"):
            fetcher.normalize_payload(
                "TEST",
                "https://example.test",
                payload,
                "2026-07-23T10:00:00+00:00",
            )


if __name__ == "__main__":
    unittest.main()
