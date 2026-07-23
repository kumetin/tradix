#!/usr/bin/env python3
"""Generate constant-name HTML bookmark pages for recurring stock reviews."""

import argparse
import csv
import html
import importlib.util
import math
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FEATURES = ROOT / "data/stock/features/daily"
OUTPUT = ROOT / "artifacts/stock/bookmarks"
TIPRANKS_SUMMARY = ROOT / "data/stock/tipranks-analysts-summary"
TIPRANKS_ACTIVITY = ROOT / "data/stock/tipranks-analysts-activity"
ETF_TIPRANKS_SUMMARY = ROOT / "data/etf/tipranks-analysts-summary"
CALCULATION_DATE = date.today().isoformat()
PE_FILE = ROOT / "data/stock/pe-valuation-summary/{}.csv".format(date.today().year)


def latest_local_cutoff():
    dates = []
    for path in sorted(FEATURES.glob("*/SPY.csv")):
        with path.open(newline="") as handle:
            for row in csv.DictReader(handle):
                if row.get("date", "") > CALCULATION_DATE:
                    continue
                try:
                    float(row.get("adj_close", ""))
                except (TypeError, ValueError):
                    continue
                dates.append(row["date"])
    return max(dates) if dates else CALCULATION_DATE


CUTOFF = latest_local_cutoff()


def load_evaluator():
    path = ROOT / "stages/setup-evaluators/lower_risk_swing_entry.py"
    spec = importlib.util.spec_from_file_location("bookmark_setup_evaluator", str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


EVALUATOR = load_evaluator()


def number(value):
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def money(value):
    return "N/A" if value is None else "${:,.2f}".format(value)


def signed(value):
    return "N/A" if value is None else "{:+.2f}%".format(value)


def load_feature_rows(ticker):
    rows = []
    for path in sorted(FEATURES.glob("*/{}.csv".format(ticker))):
        with path.open(newline="") as handle:
            rows.extend(csv.DictReader(handle))
    return [
        row for row in rows
        if row.get("date", "") <= CUTOFF and number(row.get("adj_close")) is not None
    ]


def watchlist(path):
    groups = {}
    group = "Watchlist"
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if line.startswith("## "):
            group = line[3:].strip()
            continue
        candidates = []
        if "," in line:
            candidates.extend(piece.strip() for piece in line.split(":")[-1].split(","))
        match = re.match(r"-\s+([A-Z0-9.]+)\b", line)
        if match:
            candidates.append(match.group(1))
        for ticker in candidates:
            if re.fullmatch(r"[A-Z0-9.]+", ticker):
                groups.setdefault(ticker, group)
    return groups


def latest_tipranks(ticker):
    result = {"upside": None, "count": None}
    etf_path = ETF_TIPRANKS_SUMMARY / "{}.csv".format(ticker)
    stock_path = TIPRANKS_SUMMARY / "{}.csv".format(ticker)
    if etf_path.exists():
        with etf_path.open(newline="") as handle:
            rows = [
                row for row in csv.DictReader(handle)
                if row.get("date", "") <= CALCULATION_DATE
            ]
        if rows:
            row = sorted(rows, key=lambda item: item["date"])[-1]
            result["upside"] = number(row.get("average_forecast_upside_90d"))
    elif stock_path.exists():
        with stock_path.open(newline="") as handle:
            rows = [
                row for row in csv.DictReader(handle)
                if row.get("scrape_date", "") <= CALCULATION_DATE
            ]
        if rows:
            row = sorted(rows, key=lambda item: item["scrape_date"])[-1]
            result["upside"] = number(row.get("average_forecast_upside_90d"))
    activity = TIPRANKS_ACTIVITY / "{}.csv".format(ticker)
    if activity.exists():
        end = datetime.strptime(CALCULATION_DATE, "%Y-%m-%d").date()
        start = end - timedelta(days=29)
        names = set()
        with activity.open(newline="") as handle:
            for row in csv.DictReader(handle):
                try:
                    activity_date = datetime.strptime(row["activity_date"], "%Y-%m-%d").date()
                except (KeyError, ValueError):
                    continue
                if start <= activity_date <= end and row.get("analyst_name"):
                    names.add(row["analyst_name"])
        if names:
            result["count"] = len(names)
    return result


def pe_observations():
    observations = {}
    if not PE_FILE.exists():
        return observations
    with PE_FILE.open(newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("scrape_date", "") <= CALCULATION_DATE:
                current = observations.get(row["ticker"])
                if current is None or row["scrape_date"] >= current["scrape_date"]:
                    observations[row["ticker"]] = row
    return observations


PE = pe_observations()


def metric_record(ticker, category=""):
    rows = load_feature_rows(ticker)
    empty = {
        "ticker": ticker, "category": category, "rows": rows, "setup": None,
        "evaluation": None, "price": None, "r1w": None, "r2w": None,
        "r1m": None, "momentum": None, "atr": None, "atr_pct": None,
        "distance_high": None, "sma20": None, "sma50": None, "sma200": None,
        "vol5_vs20": None, "support": None, "resistance": None,
    }
    if not rows:
        return empty
    close = [number(row["adj_close"]) for row in rows]
    high = [number(row["adj_high"]) for row in rows]
    low = [number(row["adj_low"]) for row in rows]
    volume = [number(row["volume"]) for row in rows]
    latest = rows[-1]

    def trailing_return(sessions):
        if len(close) <= sessions:
            return None
        return (close[-1] / close[-1 - sessions] - 1) * 100

    true_ranges = [
        max(high[index] - low[index],
            abs(high[index] - close[index - 1]),
            abs(low[index] - close[index - 1]))
        for index in range(1, len(rows))
    ]
    atr = sum(true_ranges[-14:]) / 14 if len(true_ranges) >= 14 else None
    setup = EVALUATOR.LowerRiskSwingEntryEvaluator.construct_setup(ticker, rows)
    evaluation = EVALUATOR.LowerRiskSwingEntryEvaluator.evaluate(setup.inputs)
    empty.update({
        "setup": setup,
        "evaluation": evaluation,
        "price": close[-1],
        "r1w": trailing_return(5),
        "r2w": trailing_return(10),
        "r1m": trailing_return(21),
        "momentum": (close[-22] / close[-253] - 1) * 100 if len(close) >= 253 else None,
        "atr": atr,
        "atr_pct": atr / close[-1] * 100 if atr else None,
        "distance_high": (close[-1] / max(high) - 1) * 100,
        "sma20": number(latest.get("sma_20")),
        "sma50": number(latest.get("sma_50")),
        "sma200": number(latest.get("sma_200")),
        "vol5_vs20": ((sum(volume[-5:]) / 5) / (sum(volume[-20:]) / 20) - 1) * 100
        if len(volume) >= 20 else None,
        "support": min(low[-20:]) if len(low) >= 20 else min(low),
        "resistance": max(high[-20:]) if len(high) >= 20 else max(high),
    })
    return empty


def technical(record):
    if record["price"] is None:
        return "No compatible daily-stock history through the cutoff."
    relations = []
    for label, key in (("20d", "sma20"), ("50d", "sma50"), ("200d", "sma200")):
        average = record[key]
        if average is not None:
            relations.append("{} {} {}".format("above" if record["price"] > average else "below", label, money(average)))
    volume = record["vol5_vs20"]
    volume_text = "volume N/A" if volume is None else "{} volume ({:+.0f}% vs 20d)".format(
        "elevated" if volume > 15 else "light" if volume < -15 else "normal", volume)
    return "{}; {}; {}; support {}, resistance {}.".format(
        money(record["price"]), ", ".join(relations), volume_text,
        money(record["support"]), money(record["resistance"]))


def continuation(record):
    if record["price"] is None:
        return "N/A"
    above20 = record["sma20"] is not None and record["price"] > record["sma20"]
    above50 = record["sma50"] is not None and record["price"] > record["sma50"]
    if above20 and above50 and (record["r2w"] or 0) > 0:
        lead = "Constructive; trend and two-week momentum agree."
    elif above20:
        lead = "Improving, but overhead resistance still needs confirmation."
    else:
        lead = "Weak or unconfirmed; wait for a 20-day reclaim or support base."
    if record["atr_pct"] is not None and record["atr_pct"] > 7:
        lead += " High ATR raises exhaustion and sizing risk."
    return lead


def rank_records(records):
    setups = [record["setup"] for record in records if record["setup"] is not None]
    ranked = EVALUATOR.LowerRiskSwingEntryEvaluator.score_setups(setups)
    setup_rank = {item.setup.ticker: index for index, item in enumerate(ranked, 1)}
    eligible = sorted(
        ((record["momentum"], record["ticker"]) for record in records if record["momentum"] is not None),
        reverse=True,
    )
    momentum_rank = {ticker: index for index, (_, ticker) in enumerate(eligible, 1)}
    for record in records:
        record["setup_rank"] = setup_rank.get(record["ticker"])
        record["momentum_rank"] = momentum_rank.get(record["ticker"])
        record["momentum_count"] = len(eligible)
    return sorted(records, key=lambda record: (
        record["setup_rank"] is None,
        record["setup_rank"] if record["setup_rank"] is not None else 10 ** 6,
        record["ticker"],
    ))


def analyst_cell(ticker, analyst):
    if analyst["upside"] is None:
        return "N/A"
    url = "https://www.tipranks.com/stocks/{}/forecast".format(ticker.lower())
    return '<a href="{}">{}</a>'.format(url, signed(analyst["upside"]))


def technical_cell(record):
    ticker = record["ticker"]
    chart_url = "https://finance.yahoo.com/chart/{}".format(ticker)
    return '{} <a href="{}">{}</a>'.format(
        html.escape(technical(record)),
        html.escape(chart_url, quote=True),
        html.escape(ticker),
    )


def fomo_current_cell(record, sale):
    current = record["price"]
    sell_price = number(sale.get("price"))
    if current is None:
        return "N/A"
    difference = (current / sell_price - 1) * 100 if sell_price else None
    if difference is None:
        return money(current)
    css_class = "gain" if difference > 0 else "loss" if difference < 0 else "flat"
    return '<span class="{}">{} ({})</span>'.format(
        css_class, money(current), signed(difference))


def table_row(record, review_type, extras):
    ticker = record["ticker"]
    analyst = latest_tipranks(ticker)
    pe = PE.get(ticker, {})
    own_pe = number(pe.get("own_5y_distance_pct"))
    sector_pe = number(pe.get("sector_distance_pct"))
    values = [
        '<td class="ticker">{}</td>'.format(html.escape(ticker)),
        "<td>{}</td>".format(signed(record["r1w"])),
        "<td>{}</td>".format(signed(record["r2w"])),
        '<td class="narrative">{}</td>'.format(technical_cell(record)),
        '<td class="narrative">{}</td>'.format(html.escape(continuation(record))),
    ]
    if review_type == "fomo":
        sale = extras.get(ticker, {})
        values.extend([
            "<td>{}</td>".format(fomo_current_cell(record, sale)),
            "<td>{}</td>".format(html.escape(sale.get("display", "N/A"))),
        ])
    if review_type == "portfolio":
        position = extras[ticker]
        average = number(position.get("CostBasisPrice"))
        current = number(position.get("MarkPrice"))
        pnl_pct = (current / average - 1) * 100 if average and current else None
        values.extend([
            "<td>{}</td>".format(money(average)),
            "<td>{}</td>".format(money(current)),
            "<td>{}</td>".format(signed(pnl_pct)),
            "<td>{}</td>".format(money(number(position.get("FifoPnlUnrealized")))),
        ])
    setup_rank = "{}/{}".format(record["setup_rank"], len(extras) if review_type == "portfolio" else record["_total"]) if record["setup_rank"] else "N/A"
    momentum_rank = "{}/{}".format(record["momentum_rank"], record["momentum_count"]) if record["momentum_rank"] else "N/A"
    values.extend([
        "<td>{}</td>".format(setup_rank),
        "<td>{}</td>".format(momentum_rank),
        "<td>{}</td>".format(signed(record["momentum"])),
        "<td>{}</td>".format(signed(record["r1m"])),
        "<td>{}</td>".format(
            "{} / {}".format(money(record["atr"]), signed(record["atr_pct"]))
            if record["atr"] is not None else "N/A"),
        "<td>{}</td>".format(analyst_cell(ticker, analyst)),
        "<td>{}</td>".format(analyst["count"] if analyst["count"] is not None else "N/A"),
        "<td>{}</td>".format(signed(record["distance_high"])),
        "<td>{}</td>".format(signed(own_pe)),
        "<td>{}</td>".format(signed(sector_pe)),
    ])
    return "<tr>{}</tr>".format("".join(values))


def write_page(filename, title, records, review_type="watchlist", extras=None, data_gaps=None):
    extras = extras or {}
    records = rank_records(records)
    for record in records:
        record["_total"] = len(records)
    headers = ["Ticker", "Last 1W", "Last 2W", "Technical Condition", "Continuation View"]
    if review_type == "fomo":
        headers.extend(["Current Price", "Sell Price"])
    if review_type == "portfolio":
        headers.extend(["Average Buy Price", "Current Price", "Unrealized P/L %", "Unrealized P/L"])
    headers.extend([
        "Setup Rank", "Momentum Rank", "12-1 Momentum %", "Last 1M", "ATR-14",
        "Analyst Upside %", "Analysts Last 30d", "Distance from High %",
        "P/E vs own 5Y avg %", "P/E vs Sector %",
    ])
    body = "\n".join(table_row(record, review_type, extras) for record in records)
    header = "".join("<th>{}</th>".format(html.escape(item)) for item in headers)
    gaps = "; ".join(data_gaps or []) or "None."
    document = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} ({calculation_date})</title>
<style>
:root{{color-scheme:light dark}} body{{margin:24px;font:14px/1.45 system-ui,sans-serif}}
h1{{margin:0 0 14px}} .scroll{{overflow-x:auto;width:100%;padding-bottom:12px;border:1px solid #8886}}
table{{min-width:2850px;border-collapse:collapse;background:Canvas}} th,td{{padding:8px 10px;border:1px solid #8886;text-align:right;vertical-align:top}}
th{{position:sticky;top:0;background:Canvas;white-space:nowrap;cursor:pointer;user-select:none}}
th::after{{content:" ↕";opacity:.45}} th[aria-sort="ascending"]::after{{content:" ↑";opacity:1}} th[aria-sort="descending"]::after{{content:" ↓";opacity:1}}
th:first-child,td:first-child{{position:sticky;left:0;background:Canvas;z-index:1}}
.ticker{{font-weight:700;text-align:left;white-space:nowrap}} .narrative{{width:300px;max-width:300px;text-align:left;white-space:normal}}
.gain{{color:#c62828;font-weight:700}} .loss{{color:#14833b;font-weight:700}} .flat{{font-weight:700}}
.meta{{margin-top:18px;max-width:1200px}} code{{white-space:nowrap}}
</style></head><body>
<h1>{title} <span>({calculation_date})</span></h1><h2>Forcast Table</h2>
<div class="scroll"><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></div>
<div class="meta">
<p><strong>Decision cutoff:</strong> {cutoff}. <strong>Analyst collection date:</strong> {calculation_date}.</p>
<p><strong>Momentum universe:</strong> this page's complete resolved universe; rank denominator contains only symbols with 253 valid sessions.</p>
<p><strong>Sector methodology:</strong> a trailing sector comparison is shown only when a consistent verified benchmark exists; otherwise N/A.</p>
{fomo_note}
<p><strong>Material data gaps:</strong> {gaps}</p>
<p>This is a research watchlist review, not certainty or personalized financial advice.</p>
</div>
<script>
document.querySelectorAll("table").forEach(function(table) {{
  var headers = Array.from(table.tHead.rows[0].cells);
  var body = table.tBodies[0];
  var direction = {{}};

  function valueOf(cell) {{
    var text = cell.textContent.trim();
    if (!text || text === "N/A") return {{missing:true, value:""}};
    var rank = text.match(/^([+-]?\\d+(?:\\.\\d+)?)\\s*\\/\\s*\\d+$/);
    if (rank) return {{missing:false, value:Number(rank[1])}};
    var numeric = text.match(/^[\\s$]*([+-]?[\\d,]+(?:\\.\\d+)?)/);
    if (numeric && (/[\\d$%]/.test(text))) {{
      return {{missing:false, value:Number(numeric[1].replace(/,/g, ""))}};
    }}
    return {{missing:false, value:text.toLocaleLowerCase()}};
  }}

  headers.forEach(function(header, column) {{
    header.tabIndex = 0;
    header.title = "Click to sort";
    function sortColumn() {{
      var ascending = direction[column] !== "ascending";
      direction = {{}};
      direction[column] = ascending ? "ascending" : "descending";
      headers.forEach(function(item) {{ item.removeAttribute("aria-sort"); }});
      header.setAttribute("aria-sort", direction[column]);
      var rows = Array.from(body.rows).map(function(row, index) {{
        return {{row:row, index:index, key:valueOf(row.cells[column])}};
      }});
      rows.sort(function(a, b) {{
        if (a.key.missing !== b.key.missing) return a.key.missing ? 1 : -1;
        if (a.key.value === b.key.value) return a.index - b.index;
        var comparison = typeof a.key.value === "number"
          ? a.key.value - b.key.value
          : String(a.key.value).localeCompare(String(b.key.value), undefined, {{numeric:true}});
        return ascending ? comparison : -comparison;
      }});
      rows.forEach(function(item) {{ body.appendChild(item.row); }});
    }}
    header.addEventListener("click", sortColumn);
    header.addEventListener("keydown", function(event) {{
      if (event.key === "Enter" || event.key === " ") {{
        event.preventDefault();
        sortColumn();
      }}
    }});
  }});
}});
</script></body></html>""".format(
        title=html.escape(title), calculation_date=CALCULATION_DATE, cutoff=CUTOFF,
        header=header, body=body, gaps=html.escape(gaps),
        fomo_note=(
            "<p><strong>FOMO current-price comparison:</strong> percentage in "
            "parentheses is current price versus the matched sell execution; "
            "red is above the sell price and green is below it.</p>"
            if review_type == "fomo" else ""
        ))
    OUTPUT.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT / (filename + ".tmp")
    temporary.write_text(document)
    temporary.replace(OUTPUT / filename)


def fomo_sales(path):
    wanted = {"NVDU", "DRAM", "ETHA", "ALB", "IREN", "LUNR", "IBIT"}
    matches = {}
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("Symbol") in wanted and row.get("Buy/Sell") == "SELL" and row.get("TradeDate") == "20260706":
                ticker = row["Symbol"]
                sell_price = number(row.get("TradePrice"))
                matches[ticker] = {
                    "price": sell_price,
                    "display": "{} ({})".format(
                        money(sell_price),
                        "{}-{}-{}".format(
                            row["TradeDate"][:4],
                            row["TradeDate"][4:6],
                            row["TradeDate"][6:],
                        ),
                    ),
                }
    return matches


def portfolio_positions(path):
    with path.open(newline="") as handle:
        return {row["Symbol"]: row for row in csv.DictReader(handle)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--portfolio-csv", type=Path, required=True)
    parser.add_argument("--trades-csv", type=Path, required=True)
    args = parser.parse_args()

    ai = watchlist(ROOT / "watchlists/ai-infrastructure.md")
    porter = watchlist(ROOT / "watchlists/porter-list.md")
    fomo = fomo_sales(args.trades_csv)
    portfolio = portfolio_positions(args.portfolio_csv)

    write_page("ai-infrastructure.html", "AI Infrastructure Watchlist Review",
               [metric_record(ticker, group) for ticker, group in ai.items()],
               data_gaps=["Current TipRanks and P/E observations are unavailable for most symbols and are shown as N/A."])
    porter_gaps = ["TSE: configured providers returned no current daily history."]
    write_page("porter.html", "Porter Watchlist Review",
               [metric_record(ticker, group) for ticker, group in porter.items()],
               data_gaps=porter_gaps + ["Current TipRanks and P/E observations are unavailable and are shown as N/A."])
    write_page("fomo.html", "FOMO Watchlist Review",
               [metric_record(ticker, "Cut-loss re-entry") for ticker in fomo],
               review_type="fomo", extras=fomo,
               data_gaps=["TipRanks does not provide applicable consensus data for the four fund products."])
    write_page("portfolio.html", "Portfolio Review",
               [metric_record(ticker, row.get("AssetClass", "")) for ticker, row in portfolio.items()],
               review_type="portfolio", extras=portfolio,
               data_gaps=["OPENL, OPENW, and OPENZ are warrants without compatible daily-stock histories; technical fields are N/A."])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
