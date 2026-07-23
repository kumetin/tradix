#!/usr/bin/env python3
"""Behavioral tests for the canonical daily-price integrity audit."""

import csv
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/market-data-fetchers/audit_daily_stock_prices.py"
SPEC = importlib.util.spec_from_file_location("audit_daily_stock_prices", MODULE_PATH)
audit_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit_module
SPEC.loader.exec_module(audit_module)


FIELDS = [
    "symbol", "datetime", "date", "bar_size", "open", "high", "low", "close",
    "adj_close", "volume", "currency", "exchange_timezone", "source",
]


class DailyStockPriceAuditTest(unittest.TestCase):
    def write_symbol(self, root: Path, symbol: str, timezone: str, dates, blank_date=None):
        path = root / "2024" / (symbol + ".csv")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            for date in dates:
                blank = date == blank_date
                writer.writerow({
                    "symbol": symbol,
                    "datetime": date + "T14:30:00+00:00",
                    "date": date,
                    "bar_size": "1d",
                    "open": "" if blank else "10",
                    "high": "" if blank else "11",
                    "low": "" if blank else "9",
                    "close": "" if blank else "10",
                    "adj_close": "" if blank else "10",
                    "volume": "" if blank else "100",
                    "currency": "USD",
                    "exchange_timezone": timezone,
                    "source": "fixture",
                })

    def test_clips_history_and_does_not_apply_spy_calendar_to_foreign_symbol(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            calendar = ["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"]
            self.write_symbol(root, "SPY", "America/New_York", calendar)
            self.write_symbol(root, "LATE", "America/New_York", calendar[2:])
            self.write_symbol(root, "GAP", "America/New_York", [calendar[0], calendar[2]])
            self.write_symbol(root, "TW", "Asia/Taipei", [calendar[0], calendar[2]])

            report = audit_module.audit(root, "SPY")

            self.assertIn("`GAP`: `1` gaps; 2024-01-03", report)
            self.assertNotIn("`LATE`:", report)
            self.assertIn("`Asia/Taipei`: `1` symbols; no missing-session claim made", report)

    def test_reports_blank_ohlcv_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dates = ["2024-01-02", "2024-01-03"]
            self.write_symbol(root, "SPY", "America/New_York", dates)
            self.write_symbol(root, "BAD", "America/New_York", dates, blank_date="2024-01-03")

            report = audit_module.audit(root, "SPY")

            self.assertIn("`BAD`: 2024-01-03", report)


if __name__ == "__main__":
    unittest.main()
