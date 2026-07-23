#!/usr/bin/env python3
"""Build point-in-time institutional snapshots from SEC Form 13F datasets."""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import io
import json
import re
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
SEC_BASE = "https://www.sec.gov/files/structureddata/data/form-13f-data-sets"
USER_AGENT = "Tradix research contact@example.com"
OUTPUT_ROOT = ROOT / "data/stock/institutions/quarterly"
CACHE_ROOT = Path("/tmp/tradix-sec-form13f-cache")
PERIODS = tuple(f"{y}q{q}" for y in range(2020, 2026) for q in range(1, 5)
                if "2020q4" <= f"{y}q{q}" <= "2025q1")
ARCHIVE_NAMES = {
    "2024q1": "01jan2024-29feb2024_form13f.zip",
    "2024q2": "01mar2024-31may2024_form13f.zip",
    "2024q3": "01jun2024-31aug2024_form13f.zip",
    "2024q4": "01sep2024-30nov2024_form13f.zip",
    "2025q1": "01dec2024-28feb2025_form13f.zip",
}
GENERIC = {"THE", "INC", "CORP", "CORPORATION", "CO", "COS", "COMPANY",
           "PLC", "LTD", "LIMITED", "HOLDING", "HOLDINGS", "GROUP", "DEL",
           "NEW", "NV", "SA", "DE", "MA", "MI", "CA"}
ALIASES = {
    "MAS": ("MASCO",), "NEM": ("NEWMONT",), "OXY": ("OCCIDENTALPETROLEUM",),
    "VRSN": ("VERISIGN",), "AMT": ("AMERICANTOWER", "AMERICANTOWERA"),
    "CRH": ("CRH",), "VRTX": ("VERTEXPHARMACEUTICALS",),
    "DVN": ("DEVONENERGY", "DEVONENERGYNE"),
    "HIG": ("HARTFORDFINANCIAL", "HARTFORDFINANCIALSERVICES"),
    "PHM": ("PULTEGROUP",), "RVTY": ("REVVITY", "PERKINELMER"),
    "TJX": ("TJX",), "VLO": ("VALEROENERGY",),
    "WBD": ("WARNERBROSDISCOVERY", "DISCOVERY"), "DHI": ("DRHORTON",),
    "HRL": ("HORMELFOODS",), "IDXX": ("IDEXXLABORATORIES",),
    "BAC": ("BANKOFAMERICA",), "BG": ("BUNGEGLOBAL", "BUNGE"),
    "COR": ("CENCORA", "AMERISOURCEBERGEN"), "IEX": ("IDEX",),
    "J": ("JACOBSSOLUTIONS", "JACOBSENGINEERING"),
    "META": ("METAPLATFORMS", "FACEBOOK"), "TSCO": ("TRACTORSUPPLY",),
    "WFC": ("WELLSFARGO",),
}
COLUMNS = ["symbol", "report_period_end", "available_date",
           "total_institutional_shares_held", "net_reported_shares_change",
           "institutional_holders", "source", "source_url", "fetched_at_utc"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-period", default="2020q4")
    parser.add_argument("--end-period", default="2025q1")
    parser.add_argument("--universe", action="append", type=Path)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    periods = [p for p in PERIODS if args.start_period <= p <= args.end_period]
    paths = args.universe or sorted(
        (ROOT / "configuration/universes").glob("random-sp500-50-*.md"))
    tickers = sorted({t for path in paths for t in parse_universe(path)})
    aliases = build_aliases(tickers, fetch_company_names())
    events, matched = [], set()
    CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    archives = []
    for period in periods:
        archive = CACHE_ROOT / f"{period}.zip"
        archive_name = ARCHIVE_NAMES.get(period, f"{period}_form13f.zip")
        if not archive.exists():
            download(f"{SEC_BASE}/{archive_name}", archive)
        archives.append((period, archive))
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(read_archive, archive, aliases): period
            for period, archive in archives
        }
        for future in concurrent.futures.as_completed(futures):
            period = futures[future]
            found, names = future.result()
            events.extend(found)
            matched.update(names)
            print(f"{period}: {len(found)} matched filing/security events", flush=True)
    snapshots = replay(events)
    write_snapshots(args.output_root, snapshots)
    print(f"wrote {sum(map(len, snapshots.values()))} snapshots for "
          f"{len(snapshots)} tickers", flush=True)
    print(f"matched {len(matched)}/{len(tickers)} tickers", flush=True)
    if set(tickers) - matched:
        print("unmatched: " + ", ".join(sorted(set(tickers) - matched)), flush=True)
    return 0


def read_archive(path: Path, aliases: dict[str, list[str]]
                 ) -> tuple[list[dict[str, Any]], set[str]]:
    with zipfile.ZipFile(path) as archive:
        submissions = {r["ACCESSION_NUMBER"]: r
                       for r in tsv_rows(archive, "SUBMISSION.tsv")
                       if r["SUBMISSIONTYPE"] in {"13F-HR", "13F-HR/A"}}
        amendments = {r["ACCESSION_NUMBER"]: r.get("AMENDMENTTYPE", "")
                      for r in tsv_rows(archive, "COVERPAGE.tsv")}
        holdings: dict[tuple[str, str], int] = defaultdict(int)
        matched = set()
        for row in tsv_rows(archive, "INFOTABLE.tsv"):
            accession = row["ACCESSION_NUMBER"]
            if accession not in submissions or row.get("PUTCALL"):
                continue
            ticker = resolve(normalize(row["NAMEOFISSUER"]),
                             row.get("TITLEOFCLASS", ""), aliases)
            if ticker is None:
                continue
            try:
                shares = int(float(row["SSHPRNAMT"]))
            except (TypeError, ValueError):
                continue
            holdings[(accession, ticker)] += shares
            matched.add(ticker)
        result = []
        for (accession, ticker), shares in holdings.items():
            sub = submissions[accession]
            result.append({
                "accession": accession, "ticker": ticker, "shares": shares,
                "filing_date": sec_date(sub["FILING_DATE"]),
                "report_period": sec_date(sub["PERIODOFREPORT"]),
                "cik": sub["CIK"],
                "amendment_type": amendments.get(accession, ""),
            })
        return result, matched


def replay(events: list[dict[str, Any]]) -> dict[str, list[dict[str, str]]]:
    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        by_date[event["filing_date"]].append(event)
    reports: dict[tuple[str, str], dict[str, int]] = defaultdict(dict)
    latest: dict[tuple[str, str], str] = {}
    holding: dict[str, dict[str, int]] = defaultdict(dict)
    delta: dict[str, dict[str, int | None]] = defaultdict(dict)
    output: dict[str, list[dict[str, str]]] = defaultdict(list)
    for date in sorted(by_date):
        changed = set()
        for event in sorted(by_date[date], key=lambda x: x["accession"]):
            ticker, cik, period = event["ticker"], event["cik"], event["report_period"]
            manager_key = (ticker, cik)
            manager_reports = reports[manager_key]
            if "ADD" in event["amendment_type"].upper():
                manager_reports[period] = manager_reports.get(period, 0) + event["shares"]
            else:
                manager_reports[period] = event["shares"]
            if period < latest.get(manager_key, ""):
                continue
            prior_periods = [p for p in manager_reports if p < period]
            prior = manager_reports[max(prior_periods)] if prior_periods else None
            latest[manager_key] = period
            holding[ticker][cik] = manager_reports[period]
            delta[ticker][cik] = (
                manager_reports[period] - prior if prior is not None else None
            )
            changed.add(ticker)
        for ticker in changed:
            managers = holding[ticker]
            deltas = [value for value in delta[ticker].values() if value is not None]
            output[ticker].append({
                "symbol": ticker,
                "report_period_end": max(latest[(ticker, cik)] for cik in managers),
                "available_date": date,
                "total_institutional_shares_held": str(sum(managers.values())),
                "net_reported_shares_change": str(sum(deltas)) if deltas else "",
                "institutional_holders": str(len(managers)),
                "source": "sec_form13f_derived",
                "source_url": "https://www.sec.gov/data-research/sec-markets-data/form-13f-data-sets",
                "fetched_at_utc": "",
            })
    return output


def write_snapshots(root: Path, snapshots: dict[str, list[dict[str, str]]]) -> None:
    for ticker, rows in snapshots.items():
        by_year: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in rows:
            by_year[row["available_date"][:4]].append(row)
        for year, additions in by_year.items():
            path = root / year / f"{ticker}.csv"
            existing = []
            if path.exists():
                with path.open(newline="", encoding="utf-8") as handle:
                    existing = list(csv.DictReader(handle))
            merged = {(r["available_date"], r["source"]): r
                      for r in existing + additions}
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=COLUMNS)
                writer.writeheader()
                writer.writerows(sorted(merged.values(),
                                        key=lambda r: r["available_date"]))


def build_aliases(tickers: list[str], names: dict[str, str]
                  ) -> dict[str, list[str]]:
    result: dict[str, list[str]] = defaultdict(list)
    for ticker in tickers:
        for alias in {normalize(names.get(ticker, ticker)), *ALIASES.get(ticker, ())}:
            result[alias].append(ticker)
    return result


def resolve(issuer: str, title: str, aliases: dict[str, list[str]]) -> str | None:
    candidates = aliases.get(issuer, [])
    if len(candidates) == 1:
        ticker = candidates[0]
        if ticker == "BRK-B" and "B" not in title.upper():
            return None
        return ticker
    upper = title.upper()
    if "GOOGL" in candidates and ("CL A" in upper or "CLASS A" in upper):
        return "GOOGL"
    if "GOOG" in candidates and ("CL C" in upper or "CLASS C" in upper):
        return "GOOG"
    return None


def fetch_company_names() -> dict[str, str]:
    request = urllib.request.Request(
        "https://www.sec.gov/files/company_tickers.json",
        headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.load(response)
    return {row["ticker"].replace(".", "-"): row["title"]
            for row in payload.values()}


def download(url: str, path: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=180) as response, path.open("wb") as out:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)


def tsv_rows(archive: zipfile.ZipFile, name: str) -> Iterable[dict[str, str]]:
    with archive.open(name) as raw:
        yield from csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig"),
                                  delimiter="\t")


def parse_universe(path: Path) -> list[str]:
    return [line[3:-1] for line in path.read_text(encoding="utf-8").splitlines()
            if line.startswith("- `") and line.endswith("`")]


def normalize(value: str) -> str:
    return "".join(word for word in re.sub(r"[^A-Z0-9 ]", " ", value.upper()).split()
                   if word not in GENERIC)


def sec_date(value: str) -> str:
    day, month, year = value.split("-")
    months = {name: str(i).zfill(2) for i, name in enumerate(
        ("", "JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG",
         "SEP", "OCT", "NOV", "DEC")) if name}
    return f"{year}-{months[month.upper()]}-{day.zfill(2)}"


if __name__ == "__main__":
    raise SystemExit(main())
