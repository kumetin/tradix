"""Test canonical-data inventory and missing-row detection.

Parameters:
    None; unittest discovers the test methods.
External sources:
    The local ``repair-canonical-data.py`` module and synthetic temporary CSVs.
Side effects:
    Creates automatically cleaned temporary directories/files and emits
    unittest results; canonical repository data is not modified.
Examples:
    Run this test module directly::

        python3 tests/test_repair_canonical_data.py

    Run it through unittest discovery::

        python3 -m unittest discover -s tests -p 'test_repair_canonical_data.py'
"""

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/repair-canonical-data.py"
SPEC = importlib.util.spec_from_file_location("repair_canonical_data", MODULE_PATH)
repair = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(repair)


class RepairCanonicalDataTest(unittest.TestCase):
    def test_unchanged_file_uses_hash_fast_path(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "SPY.csv"
            path.write_text("symbol,date,close\nSPY,2026-07-16,750\n")
            entry = repair.inventory_entry(path, "price", repair.file_sha256(path))

            self.assertEqual([], repair.missing_keys(entry, path))

    def test_deleted_date_is_reported_from_inventory(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "SPY.csv"
            path.write_text(
                "symbol,date,close\n"
                "SPY,2026-07-15,754\n"
                "SPY,2026-07-16,750\n"
            )
            entry = repair.inventory_entry(path, "price", repair.file_sha256(path))
            path.write_text("symbol,date,close\nSPY,2026-07-15,754\n")

            self.assertEqual(["2026-07-16"], repair.missing_keys(entry, path))


if __name__ == "__main__":
    unittest.main()
