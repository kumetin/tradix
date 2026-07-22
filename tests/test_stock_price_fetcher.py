"""Test canonical normalization performed by the stock-price fetcher.

Parameters:
    None; unittest discovers the test methods.
External sources:
    The local ``fetch_stock_prices.py`` module and in-memory provider payloads.
    No live provider requests are made.
Side effects:
    Imports the fetcher dynamically and emits unittest results; repository data
    is not modified.
Examples:
    Run this test module directly::

        python3 tests/test_stock_price_fetcher.py

    Run it through unittest discovery::

        python3 -m unittest discover -s tests -p 'test_stock_price_fetcher.py'
"""

import datetime as dt
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FETCHER_PATH = ROOT / "scripts/market-data-fetchers/fetch_stock_prices.py"
SPEC = importlib.util.spec_from_file_location("fetch_stock_prices", FETCHER_PATH)
fetcher = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(fetcher)


class StockPriceFetcherTest(unittest.TestCase):
    def test_all_providers_normalize_to_the_canonical_schema(self):
        timestamp = int(
            dt.datetime(2026, 7, 20, 13, 30, tzinfo=dt.timezone.utc).timestamp()
        )
        yahoo_rows = fetcher.parse_yahoo_payload(
            {
                "chart": {
                    "result": [
                        {
                            "timestamp": [timestamp],
                            "meta": {
                                "symbol": "AAPL",
                                "currency": "USD",
                                "exchangeTimezoneName": "America/New_York",
                            },
                            "indicators": {
                                "quote": [
                                    {
                                        "open": [210.0],
                                        "high": [212.0],
                                        "low": [209.0],
                                        "close": [211.0],
                                        "volume": [1000],
                                    }
                                ],
                                "adjclose": [{"adjclose": [211.0]}],
                            },
                        }
                    ],
                    "error": None,
                }
            },
            "AAPL",
            "1d",
        )
        twelve_data_rows = fetcher.parse_twelve_data_payload(
            {
                "meta": {
                    "symbol": "AAPL",
                    "currency": "USD",
                    "exchange_timezone": "America/New_York",
                },
                "values": [
                    {
                        "datetime": "2026-07-20",
                        "open": "210.0",
                        "high": "212.0",
                        "low": "209.0",
                        "close": "211.0",
                        "volume": "1000",
                    }
                ],
            },
            "AAPL",
            "1d",
        )

        for rows in (yahoo_rows, twelve_data_rows):
            self.assertEqual(1, len(rows))
            self.assertEqual(set(fetcher.CSV_COLUMNS), set(rows[0]))

        self.assertEqual(fetcher.YAHOO_SOURCE, yahoo_rows[0]["source"])
        self.assertEqual(fetcher.TWELVE_DATA_SOURCE, twelve_data_rows[0]["source"])


if __name__ == "__main__":
    unittest.main()
