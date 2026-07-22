#!/usr/bin/env python3
"""Inventory canonical CSV rows and refetch any rows missing since the last sync."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / ".b2-canonical-manifest.json"
PRICE_ROOT = ROOT / "data/stock/prices/daily"
FEATURE_ROOT = ROOT / "data/stock/features/daily"
ANALYST_ROOT = ROOT / "data/stock/analysts/activity"
ANALYST_KEY_COLUMNS = (
    "date",
    "datetime",
    "firm",
    "analyst",
    "from_grade",
    "to_grade",
    "from_price_target",
    "to_price_target",
    "action",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("snapshot", "repair"))
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    return parser.parse_args()


def csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def row_key(kind: str, row: dict[str, str]) -> str:
    if kind in ("price", "feature"):
        return row.get("date", "")
    return "\x1f".join(row.get(column, "") for column in ANALYST_KEY_COLUMNS)


def dataset_kind(path: Path) -> str | None:
    try:
        path.relative_to(PRICE_ROOT)
        return "price"
    except ValueError:
        pass
    try:
        path.relative_to(FEATURE_ROOT)
        return "feature"
    except ValueError:
        pass
    try:
        path.relative_to(ANALYST_ROOT)
        return "analyst"
    except ValueError:
        return None


def inventory_entry(path: Path, kind: str, sha256: str) -> dict[str, object]:
    rows = csv_rows(path)
    keys = sorted({row_key(kind, row) for row in rows if row_key(kind, row)})
    entry: dict[str, object] = {
        "kind": kind,
        "symbol": path.stem,
        "keys": "\n".join(keys),
        "sha256": sha256,
    }
    if kind == "price":
        entry["provider_symbol"] = next(
            (row.get("symbol") for row in rows if row.get("symbol")), path.stem
        )
    elif kind == "analyst":
        entry["source"] = next(
            (row.get("source") for row in rows if row.get("source")), "marketbeat"
        )
    return entry


def build_inventory(previous_files: dict[str, object] | None = None) -> dict[str, object]:
    previous_files = previous_files or {}
    files: dict[str, object] = {}
    for root in (PRICE_ROOT, FEATURE_ROOT, ANALYST_ROOT):
        for path in sorted(root.glob("*/*.csv")):
            kind = dataset_kind(path)
            if kind:
                relative = str(path.relative_to(ROOT))
                sha256 = file_sha256(path)
                previous = previous_files.get(relative)
                if isinstance(previous, dict) and previous.get("sha256") == sha256:
                    files[relative] = previous
                else:
                    files[relative] = inventory_entry(path, kind, sha256)
    return {"version": 2, "files": files}


def write_manifest(path: Path) -> None:
    previous_files: dict[str, object] = {}
    if path.exists():
        try:
            previous = json.loads(path.read_text())
            if previous.get("version") == 2 and isinstance(previous.get("files"), dict):
                previous_files = previous["files"]
        except (json.JSONDecodeError, OSError):
            pass
    inventory = build_inventory(previous_files)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(inventory, sort_keys=True, separators=(",", ":")))
    temporary.replace(path)
    print(f"canonical snapshot: files={len(inventory['files'])} manifest={path}")


def load_manifest(path: Path) -> dict[str, object]:
    if not path.exists():
        raise RuntimeError(
            f"canonical manifest is missing: {path}; bootstrap this clone before syncing"
        )
    manifest = json.loads(path.read_text())
    if manifest.get("version") != 2 or not isinstance(manifest.get("files"), dict):
        raise RuntimeError(f"unsupported canonical manifest: {path}")
    return manifest


def missing_keys(entry: dict[str, object], path: Path) -> list[str]:
    if path.exists() and entry.get("sha256") == file_sha256(path):
        return []
    kind = str(entry["kind"])
    actual = {row_key(kind, row) for row in csv_rows(path)}
    expected = set(str(entry.get("keys", "")).splitlines())
    return sorted(expected - actual)


def key_date(kind: str, key: str) -> str:
    return key if kind in ("price", "feature") else key.split("\x1f", 1)[0]


def run(command: list[str]) -> None:
    print("repair command: " + " ".join(command))
    subprocess.run(command, cwd=ROOT, check=True)


def repair(path: Path) -> None:
    manifest = load_manifest(path)
    price_ranges: dict[str, list[str]] = defaultdict(list)
    analyst_ranges: dict[tuple[str, str], list[str]] = defaultdict(list)
    feature_symbols: set[str] = set()

    for relative, raw_entry in manifest["files"].items():
        entry = dict(raw_entry)
        kind = str(entry["kind"])
        missing = missing_keys(entry, ROOT / relative)
        if not missing:
            continue
        symbol = str(entry["symbol"])
        dates = [key_date(kind, key) for key in missing if key_date(kind, key)]
        print(f"missing canonical rows: {relative} count={len(missing)}")
        if kind == "price":
            price_ranges[symbol].extend(dates)
            feature_symbols.add(symbol)
        elif kind == "feature":
            feature_symbols.add(symbol)
        elif kind == "analyst":
            source = str(entry.get("source") or "marketbeat")
            if source not in ("marketbeat", "finnhub"):
                source = "marketbeat"
            analyst_ranges[(symbol, source)].extend(dates)

    if price_ranges:
        all_dates = [date for dates in price_ranges.values() for date in dates]
        command = [
            sys.executable,
            "scripts/market-data-fetchers/backfill_daily_stock_prices.py",
            min(all_dates),
            max(all_dates),
        ]
        for symbol in sorted(price_ranges):
            command.extend(("--symbol", symbol))
        run(command)

    if feature_symbols:
        command = [
            sys.executable,
            "scripts/stock-data-enrichment/precompute_daily_stock_features.py",
        ]
        for symbol in sorted(feature_symbols):
            command.extend(("--symbol", symbol))
        run(command)

    analyst_by_source: dict[str, dict[str, list[str]]] = defaultdict(dict)
    for (symbol, source), dates in analyst_ranges.items():
        analyst_by_source[source][symbol] = dates
    for source, symbols in sorted(analyst_by_source.items()):
        dates = [date for values in symbols.values() for date in values]
        command = [
            sys.executable,
            "scripts/market-data-fetchers/fill_analyst_activity.py",
            "--start-date",
            min(dates),
            "--end-date",
            max(dates),
            "--source",
            source,
        ]
        for symbol in sorted(symbols):
            command.extend(("--symbol", symbol))
        run(command)

    unresolved = []
    for relative, raw_entry in manifest["files"].items():
        entry = dict(raw_entry)
        missing = missing_keys(entry, ROOT / relative)
        if missing:
            unresolved.append(f"{relative} ({len(missing)} rows)")
    if unresolved:
        raise RuntimeError(
            "canonical repair did not restore all expected rows; B2 was not changed:\n"
            + "\n".join(unresolved[:50])
        )
    print("canonical repair complete: all previously synchronized rows are present")


def main() -> int:
    args = parse_args()
    try:
        if args.command == "snapshot":
            write_manifest(args.manifest)
        else:
            repair(args.manifest)
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"repair-canonical-data.py: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
