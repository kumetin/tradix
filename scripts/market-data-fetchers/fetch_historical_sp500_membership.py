#!/usr/bin/env python3
"""Fetch and verify the repository's pinned historical S&P 500 membership tape."""

from __future__ import annotations

import csv
import hashlib
import io
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "data/stock/universes/sp500-historical-membership.csv"
REVISION = "a91ef88fad5ace83bed1f3452f451247295bcd18"
URL = (
    "https://raw.githubusercontent.com/hanshof/sp500_constituents/"
    f"{REVISION}/sp_500_historical_components.csv"
)
EXPECTED_SHA256 = "02f37a12c11f82218fce422ecf7d95fae1074bd96e664c262a5ea42c120d5fe9"


def main() -> int:
    with urllib.request.urlopen(URL, timeout=60) as response:
        payload = response.read()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != EXPECTED_SHA256:
        raise RuntimeError(f"membership checksum mismatch: {digest}")
    rows = list(csv.DictReader(io.StringIO(payload.decode("utf-8"))))
    if not rows or list(rows[0]) != ["date", "tickers"]:
        raise RuntimeError("unexpected membership schema")
    if any(not row["date"] or not row["tickers"] for row in rows):
        raise RuntimeError("blank membership record")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(payload)
    print(OUTPUT.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
