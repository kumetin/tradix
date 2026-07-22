#!/usr/bin/env python3
"""Generic point-in-time backtest engine for setup-evaluator signals.

Parameters:
    ``run_setup_evaluator_backtest`` accepts an evaluator adapter and a
    ``BacktestConfig`` containing tickers, window, cadence, horizons, benchmark,
    eligibility thresholds, execution assumptions, and output location.
External sources:
    Local precomputed daily feature CSVs and, for chart rendering, the local
    setup visualizer module. No live market service is contacted.
Side effects:
    Reads feature history and creates output directories containing prediction,
    outcome, summary, metadata, Markdown, HTML, and visualization artifacts.
Examples:
    Run an adapter with an explicit configuration::

        run_setup_evaluator_backtest(adapter, BacktestConfig(...))

    Parse CLI-style horizon values for a caller::

        horizons = parse_horizons(["5", "20", "60"])

Evaluator-specific code should adapt its native output to ``SetupSignal`` and
then call ``run_setup_evaluator_backtest(...)``. The engine handles local
feature loading, evaluation-date selection, point-in-time row slicing, entry
simulation, first-exit realized P&L, benchmark returns, summaries, and CSV
output.
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import html
import importlib.util
import json
import re
import statistics
import sys
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


ROOT = Path(__file__).resolve().parents[2]
FEATURE_ROOT = ROOT / "data/stock/features/daily"
SETUP_VISUALIZER_PATH = ROOT / "scripts/setup-visualizer/setup_visualizer.py"
SETUP_VISUALIZER = None

ACTION_BUY = "buy"
ACTION_WAIT = "wait"
ACTION_AVOID = "avoid"

PREDICTION_BASE_FIELDS = [
    "prediction_id",
    "evaluator_id",
    "evaluation_date",
    "ticker",
    "action",
    "setup_score",
    "evidence_score",
    "current_price",
    "entry_price",
    "buy_limit",
    "stop_loss",
    "take_profit",
]

OUTCOME_FIELDS = [
    "prediction_id",
    "evaluator_id",
    "evaluation_date",
    "ticker",
    "action",
    "entry_mode",
    "horizon_days",
    "entered",
    "entry_date",
    "entry_price",
    "exit_date",
    "exit_price",
    "exit_reason",
    "realized_return",
    "horizon_return",
    "max_favorable_excursion",
    "max_adverse_excursion",
    "hit_take_profit",
    "hit_stop_loss",
    "first_exit",
    "days_to_take_profit",
    "days_to_stop_loss",
    "benchmark_forward_return",
    "universe_equal_weight_forward_return",
]

SUMMARY_FIELDS = [
    "evaluator_id",
    "entry_mode",
    "horizon_days",
    "group_type",
    "group",
    "count",
    "entered_count",
    "win_rate",
    "average_realized_return",
    "median_realized_return",
    "average_horizon_return",
    "average_max_favorable_excursion",
    "average_max_adverse_excursion",
    "take_profit_rate",
    "stop_loss_rate",
    "average_benchmark_forward_return",
    "average_universe_equal_weight_forward_return",
]

RUN_CONFIG_FIELDS = [
    "evaluator_id",
    "scenario_slug",
    "run_timestamp",
    "config_hash",
    "tickers",
    "start_date",
    "end_date",
    "frequency",
    "horizons",
    "benchmark_ticker",
    "min_setup_score",
    "min_evidence_score",
    "run_parameters",
    "entry_actions",
    "output_dir",
]


@dataclass(frozen=True)
class SetupSignal:
    evaluator_id: str
    ticker: str
    evaluation_date: str
    action: str
    setup_score: Optional[float]
    evidence_score: Optional[float]
    current_price: Optional[float]
    entry_price: Optional[float]
    buy_limit: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    metadata: Dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class BacktestConfig:
    tickers: Sequence[str]
    start_date: dt.date
    end_date: dt.date
    frequency: str
    horizons: Sequence[int]
    benchmark_ticker: str
    output_dir: Path
    min_setup_score: Optional[float] = None
    min_evidence_score: Optional[float] = None
    run_parameters: Dict[str, object] = field(default_factory=dict)
    entry_actions: Sequence[str] = (ACTION_BUY,)
    scenario_slug: str = "manual"
    run_timestamp: Optional[str] = None
    config_hash: Optional[str] = None


class SetupEvaluatorAdapter:
    evaluator_id = ""
    extra_prediction_fields: Sequence[str] = ()
    summary_group_fields: Sequence[str] = ("action", "setup_score", "evidence_score")

    def evaluate_batch(
        self,
        evaluation_date: str,
        point_in_time_rows_by_ticker: Dict[str, List[Dict[str, str]]],
    ) -> List[SetupSignal]:
        raise NotImplementedError

    def extra_prediction_row(self, signal: SetupSignal) -> Dict[str, object]:
        return {}


def run_setup_evaluator_backtest(adapter: SetupEvaluatorAdapter, config: BacktestConfig) -> None:
    tickers = [ticker.upper() for ticker in config.tickers]
    feature_rows = {ticker: load_feature_rows(ticker) for ticker in tickers}
    benchmark_rows = load_feature_rows(config.benchmark_ticker.upper())
    evaluation_dates = select_evaluation_dates(
        feature_rows.values(),
        config.start_date,
        config.end_date,
        config.frequency,
    )

    predictions, signals_by_prediction = build_predictions(adapter, feature_rows, evaluation_dates)
    outcomes = build_outcomes(
        predictions=predictions,
        signals_by_prediction=signals_by_prediction,
        feature_rows=feature_rows,
        benchmark_rows=benchmark_rows,
        config=config,
    )
    summaries = build_summaries(adapter, predictions, outcomes)

    config.output_dir.mkdir(parents=True, exist_ok=True)
    prediction_fields = PREDICTION_BASE_FIELDS + list(adapter.extra_prediction_fields)
    write_csv(config.output_dir / "predictions.csv", prediction_fields, predictions)
    write_text(config.output_dir / "predictions.html", build_predictions_html(predictions, feature_rows))
    write_csv(config.output_dir / "outcomes.csv", OUTCOME_FIELDS, outcomes)
    write_csv(config.output_dir / "summary.csv", SUMMARY_FIELDS, summaries)
    run_config = run_config_row(adapter, config)
    write_csv(config.output_dir / "run_config.csv", RUN_CONFIG_FIELDS, [run_config])
    write_text(
        config.output_dir / "execution-report.md",
        build_execution_report(adapter, config, run_config, predictions, outcomes, summaries),
    )

    print(f"Wrote {len(predictions)} predictions to {config.output_dir / 'predictions.csv'}")
    print(f"Wrote prediction HTML to {config.output_dir / 'predictions.html'}")
    print(f"Wrote {len(outcomes)} outcomes to {config.output_dir / 'outcomes.csv'}")
    print(f"Wrote {len(summaries)} summary rows to {config.output_dir / 'summary.csv'}")
    print(f"Wrote run config to {config.output_dir / 'run_config.csv'}")
    print(f"Wrote execution report to {config.output_dir / 'execution-report.md'}")


def run_config_row(adapter: SetupEvaluatorAdapter, config: BacktestConfig) -> Dict[str, object]:
    config_hash = config.config_hash or run_config_hash(adapter.evaluator_id, config)
    return {
        "evaluator_id": adapter.evaluator_id,
        "scenario_slug": slugify(config.scenario_slug),
        "run_timestamp": config.run_timestamp or "",
        "config_hash": config_hash,
        "tickers": " ".join(config.tickers),
        "start_date": config.start_date.isoformat(),
        "end_date": config.end_date.isoformat(),
        "frequency": config.frequency,
        "horizons": " ".join(str(value) for value in config.horizons),
        "benchmark_ticker": config.benchmark_ticker,
        "min_setup_score": "" if config.min_setup_score is None else config.min_setup_score,
        "min_evidence_score": "" if config.min_evidence_score is None else config.min_evidence_score,
        "run_parameters": json.dumps(config.run_parameters, sort_keys=True, separators=(",", ":")),
        "entry_actions": " ".join(config.entry_actions),
        "output_dir": str(config.output_dir),
    }


def config_with_run_output_dir(
    adapter_id: str,
    config: BacktestConfig,
    output_root: Path,
    timestamp: Optional[str] = None,
) -> BacktestConfig:
    """Return config with a convention-based run output directory.

    Directory format:

    ``<run-timestamp>__<evaluator-id>__<scenario-slug>__<config-hash>``
    """

    run_timestamp = timestamp or utc_run_timestamp()
    scenario_slug = slugify(config.scenario_slug)
    config_hash = run_config_hash(adapter_id, config)
    run_name = "__".join((run_timestamp, slugify(adapter_id), scenario_slug, config_hash))
    return replace(
        config,
        output_dir=output_root / run_name,
        scenario_slug=scenario_slug,
        run_timestamp=run_timestamp,
        config_hash=config_hash,
    )


def run_config_hash(adapter_id: str, config: BacktestConfig) -> str:
    """Return a short deterministic hash for the normalized run configuration."""

    payload = {
        "evaluator_id": adapter_id,
        "tickers": [ticker.upper() for ticker in config.tickers],
        "start_date": config.start_date.isoformat(),
        "end_date": config.end_date.isoformat(),
        "frequency": config.frequency,
        "horizons": [int(value) for value in config.horizons],
        "benchmark_ticker": config.benchmark_ticker.upper(),
        "min_setup_score": config.min_setup_score,
        "min_evidence_score": config.min_evidence_score,
        "run_parameters": config.run_parameters,
        "entry_actions": list(config.entry_actions),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:8]


def utc_run_timestamp() -> str:
    return dt.datetime.utcnow().strftime("%Y%m%d-%H%M%SZ")


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "manual"


def parse_horizons(values: Sequence[str]) -> List[int]:
    horizons = sorted({int(value) for value in values})
    if any(value <= 0 for value in horizons):
        raise ValueError("Horizons must be positive trading-day counts")
    return horizons


def load_feature_rows(ticker: str) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for path in sorted(FEATURE_ROOT.glob(f"*/{ticker}.csv")):
        with path.open(newline="", encoding="utf-8") as handle:
            rows.extend(csv.DictReader(handle))
    rows = [row for row in rows if row.get("date") and to_float(row.get("adj_close")) is not None]
    rows.sort(key=lambda row: row["date"])
    return rows


def select_evaluation_dates(
    row_groups: Iterable[Sequence[Dict[str, str]]],
    start: dt.date,
    end: dt.date,
    frequency: str,
) -> List[str]:
    dates = sorted(
        {
            row["date"]
            for rows in row_groups
            for row in rows
            if start <= parse_date(row["date"]) <= end
        }
    )
    if frequency == "daily":
        return dates

    selected: Dict[Tuple[int, int], str] = {}
    for value in dates:
        parsed = parse_date(value)
        if frequency == "weekly":
            iso = parsed.isocalendar()
            key = (iso[0], iso[1])
        else:
            key = (parsed.year, parsed.month)
        selected[key] = value
    return list(selected.values())


def build_predictions(
    adapter: SetupEvaluatorAdapter,
    feature_rows: Dict[str, List[Dict[str, str]]],
    evaluation_dates: Sequence[str],
) -> Tuple[List[Dict[str, object]], Dict[str, SetupSignal]]:
    predictions: List[Dict[str, object]] = []
    signals_by_prediction: Dict[str, SetupSignal] = {}

    for evaluation_date in evaluation_dates:
        point_in_time_rows_by_ticker = {
            ticker: rows_through_date(rows, evaluation_date)
            for ticker, rows in feature_rows.items()
        }
        point_in_time_rows_by_ticker = {
            ticker: rows for ticker, rows in point_in_time_rows_by_ticker.items() if rows
        }
        signals = adapter.evaluate_batch(evaluation_date, point_in_time_rows_by_ticker)

        for signal in signals:
            prediction_id = f"{signal.evaluation_date}|{signal.evaluator_id}|{signal.ticker}"
            signals_by_prediction[prediction_id] = signal
            predictions.append(prediction_row(prediction_id, signal, adapter.extra_prediction_row(signal)))

    return predictions, signals_by_prediction


def prediction_row(
    prediction_id: str,
    signal: SetupSignal,
    extra_fields: Dict[str, object],
) -> Dict[str, object]:
    row = {
        "prediction_id": prediction_id,
        "evaluator_id": signal.evaluator_id,
        "evaluation_date": signal.evaluation_date,
        "ticker": signal.ticker,
        "action": signal.action,
        "setup_score": signal.setup_score,
        "evidence_score": signal.evidence_score,
        "current_price": signal.current_price,
        "entry_price": signal.entry_price,
        "buy_limit": signal.buy_limit,
        "stop_loss": signal.stop_loss,
        "take_profit": signal.take_profit,
    }
    row.update(extra_fields)
    return row


def build_outcomes(
    predictions: Sequence[Dict[str, object]],
    signals_by_prediction: Dict[str, SetupSignal],
    feature_rows: Dict[str, List[Dict[str, str]]],
    benchmark_rows: Sequence[Dict[str, str]],
    config: BacktestConfig,
) -> List[Dict[str, object]]:
    close_returns_by_key: Dict[Tuple[str, int], List[float]] = {}
    for prediction in predictions:
        signal = signals_by_prediction[str(prediction["prediction_id"])]
        rows = feature_rows[str(prediction["ticker"])]
        for horizon in config.horizons:
            value = signal_horizon_return(signal, rows, horizon)
            if isinstance(value, float):
                close_returns_by_key.setdefault((str(prediction["evaluation_date"]), horizon), []).append(value)

    universe_return_by_key = {
        key: statistics.mean(values) for key, values in close_returns_by_key.items() if values
    }

    outcomes: List[Dict[str, object]] = []
    for prediction in predictions:
        signal = signals_by_prediction[str(prediction["prediction_id"])]
        rows = feature_rows[str(prediction["ticker"])]
        eligible = signal_is_eligible(signal, config)
        for horizon in config.horizons:
            universe_return = universe_return_by_key.get((str(prediction["evaluation_date"]), horizon))
            close_outcome = close_entry_outcome(prediction, signal, rows, benchmark_rows, horizon, eligible)
            close_outcome["universe_equal_weight_forward_return"] = universe_return
            outcomes.append(close_outcome)

            limit_outcome = limit_entry_outcome(prediction, signal, rows, benchmark_rows, horizon, eligible)
            limit_outcome["universe_equal_weight_forward_return"] = universe_return
            outcomes.append(limit_outcome)
    return outcomes


def close_entry_outcome(
    prediction: Dict[str, object],
    signal: SetupSignal,
    rows: Sequence[Dict[str, str]],
    benchmark_rows: Sequence[Dict[str, str]],
    horizon: int,
    eligible: bool,
) -> Dict[str, object]:
    start_index = index_for_date(rows, signal.evaluation_date)
    entry_price = signal.entry_price if signal.entry_price is not None else signal.current_price
    if start_index is None or entry_price is None or not eligible:
        return empty_outcome(prediction, "close_entry", horizon)
    future_rows = rows[start_index + 1 : start_index + 1 + horizon]
    return measured_outcome(prediction, signal, "close_entry", horizon, future_rows, entry_price, signal.evaluation_date, benchmark_rows)


def limit_entry_outcome(
    prediction: Dict[str, object],
    signal: SetupSignal,
    rows: Sequence[Dict[str, str]],
    benchmark_rows: Sequence[Dict[str, str]],
    horizon: int,
    eligible: bool,
) -> Dict[str, object]:
    start_index = index_for_date(rows, signal.evaluation_date)
    buy_limit = signal.buy_limit
    if start_index is None or buy_limit is None or not eligible:
        return empty_outcome(prediction, "limit_entry", horizon)

    future_rows = rows[start_index + 1 : start_index + 1 + horizon]
    entry_offset = None
    for index, row in enumerate(future_rows):
        low = to_float(row.get("adj_low"))
        if low is not None and low <= buy_limit:
            entry_offset = index
            break
    if entry_offset is None:
        return empty_outcome(prediction, "limit_entry", horizon)

    entry_rows = future_rows[entry_offset:]
    entry_date = entry_rows[0]["date"]
    return measured_outcome(prediction, signal, "limit_entry", horizon, entry_rows, buy_limit, entry_date, benchmark_rows)


def signal_is_eligible(signal: SetupSignal, config: BacktestConfig) -> bool:
    if signal.action not in config.entry_actions:
        return False
    if config.min_setup_score is not None and (
        signal.setup_score is None or signal.setup_score < config.min_setup_score
    ):
        return False
    if config.min_evidence_score is not None and (
        signal.evidence_score is None or signal.evidence_score < config.min_evidence_score
    ):
        return False
    return True


def signal_horizon_return(signal: SetupSignal, rows: Sequence[Dict[str, str]], horizon: int) -> object:
    start_index = index_for_date(rows, signal.evaluation_date)
    entry_price = signal.entry_price if signal.entry_price is not None else signal.current_price
    if start_index is None or entry_price is None:
        return ""
    future_index = start_index + horizon
    if future_index >= len(rows):
        return ""
    return return_from(entry_price, to_float(rows[future_index].get("adj_close")))


def measured_outcome(
    prediction: Dict[str, object],
    signal: SetupSignal,
    entry_mode: str,
    horizon: int,
    future_rows: Sequence[Dict[str, str]],
    entry_price: float,
    entry_date: str,
    benchmark_rows: Sequence[Dict[str, str]],
) -> Dict[str, object]:
    base = empty_outcome(prediction, entry_mode, horizon)
    base["entered"] = True
    base["entry_date"] = entry_date
    base["entry_price"] = entry_price

    if not future_rows:
        return base

    horizon_exit_row = future_rows[-1]
    horizon_exit_price = to_float(horizon_exit_row.get("adj_close"))
    highs = [to_float(row.get("adj_high")) for row in future_rows]
    lows = [to_float(row.get("adj_low")) for row in future_rows]
    highs = [value for value in highs if value is not None]
    lows = [value for value in lows if value is not None]

    take_profit_hit_at = first_hit(future_rows, "adj_high", signal.take_profit, above=True)
    stop_loss_hit_at = first_hit(future_rows, "adj_low", signal.stop_loss, above=False)
    exit_reason = first_exit(take_profit_hit_at, stop_loss_hit_at)
    exit_offset = first_exit_offset(take_profit_hit_at, stop_loss_hit_at)
    if exit_reason == "take_profit":
        exit_price = signal.take_profit
    elif exit_reason == "stop_loss":
        exit_price = signal.stop_loss
    else:
        exit_price = horizon_exit_price

    if exit_offset is None:
        exit_row = horizon_exit_row
        exit_reason = "horizon_timeout"
    else:
        exit_row = future_rows[exit_offset - 1]

    base["exit_date"] = exit_row["date"]
    base["exit_price"] = exit_price
    base["exit_reason"] = exit_reason
    base["realized_return"] = return_from(entry_price, exit_price)
    base["horizon_return"] = return_from(entry_price, horizon_exit_price)
    base["max_favorable_excursion"] = favorable_excursion(entry_price, max(highs) if highs else None)
    base["max_adverse_excursion"] = adverse_excursion(entry_price, min(lows) if lows else None)
    base["hit_take_profit"] = take_profit_hit_at is not None
    base["hit_stop_loss"] = stop_loss_hit_at is not None
    base["first_exit"] = first_exit(take_profit_hit_at, stop_loss_hit_at)
    base["days_to_take_profit"] = take_profit_hit_at
    base["days_to_stop_loss"] = stop_loss_hit_at
    base["benchmark_forward_return"] = benchmark_return(benchmark_rows, str(prediction["evaluation_date"]), horizon)
    return base


def empty_outcome(prediction: Dict[str, object], entry_mode: str, horizon: int) -> Dict[str, object]:
    return {
        "prediction_id": prediction["prediction_id"],
        "evaluator_id": prediction["evaluator_id"],
        "evaluation_date": prediction["evaluation_date"],
        "ticker": prediction["ticker"],
        "action": prediction["action"],
        "entry_mode": entry_mode,
        "horizon_days": horizon,
        "entered": False,
        "entry_date": "",
        "entry_price": "",
        "exit_date": "",
        "exit_price": "",
        "exit_reason": "",
        "realized_return": "",
        "horizon_return": "",
        "max_favorable_excursion": "",
        "max_adverse_excursion": "",
        "hit_take_profit": False,
        "hit_stop_loss": False,
        "first_exit": "",
        "days_to_take_profit": "",
        "days_to_stop_loss": "",
        "benchmark_forward_return": "",
        "universe_equal_weight_forward_return": "",
    }


def build_summaries(
    adapter: SetupEvaluatorAdapter,
    predictions: Sequence[Dict[str, object]],
    outcomes: Sequence[Dict[str, object]],
) -> List[Dict[str, object]]:
    prediction_by_id = {str(row["prediction_id"]): row for row in predictions}
    grouped: Dict[Tuple[str, str, int, str, str], List[Dict[str, object]]] = {}

    for outcome in outcomes:
        prediction = prediction_by_id[str(outcome["prediction_id"])]
        for group_type, group in summary_groups(adapter, prediction):
            key = (
                str(prediction["evaluator_id"]),
                str(outcome["entry_mode"]),
                int(outcome["horizon_days"]),
                group_type,
                group,
            )
            grouped.setdefault(key, []).append(outcome)

    rows = []
    for key, values in sorted(grouped.items()):
        evaluator_id, entry_mode, horizon, group_type, group = key
        entered = [value for value in values if value["entered"]]
        returns = numeric_values(entered, "realized_return")
        rows.append(
            {
                "evaluator_id": evaluator_id,
                "entry_mode": entry_mode,
                "horizon_days": horizon,
                "group_type": group_type,
                "group": group,
                "count": len(values),
                "entered_count": len(entered),
                "win_rate": ratio(sum(1 for value in returns if value > 0), len(returns)),
                "average_realized_return": mean_or_blank(returns),
                "median_realized_return": median_or_blank(returns),
                "average_horizon_return": mean_or_blank(numeric_values(entered, "horizon_return")),
                "average_max_favorable_excursion": mean_or_blank(
                    numeric_values(entered, "max_favorable_excursion")
                ),
                "average_max_adverse_excursion": mean_or_blank(
                    numeric_values(entered, "max_adverse_excursion")
                ),
                "take_profit_rate": ratio(
                    sum(1 for value in entered if value["hit_take_profit"]), len(entered)
                ),
                "stop_loss_rate": ratio(
                    sum(1 for value in entered if value["hit_stop_loss"]), len(entered)
                ),
                "average_benchmark_forward_return": mean_or_blank(
                    numeric_values(values, "benchmark_forward_return")
                ),
                "average_universe_equal_weight_forward_return": mean_or_blank(
                    numeric_values(values, "universe_equal_weight_forward_return")
                ),
            }
        )
    return rows


def summary_groups(adapter: SetupEvaluatorAdapter, prediction: Dict[str, object]) -> List[Tuple[str, str]]:
    groups = []
    for field_name in adapter.summary_group_fields:
        value = prediction.get(field_name)
        if value in ("", None):
            continue
        if field_name in ("setup_score", "evidence_score"):
            groups.append((field_name, score_bucket(float(value))))
        else:
            groups.append((field_name, str(value)))
    return groups


def build_execution_report(
    adapter: SetupEvaluatorAdapter,
    config: BacktestConfig,
    run_config: Dict[str, object],
    predictions: Sequence[Dict[str, object]],
    outcomes: Sequence[Dict[str, object]],
    summaries: Sequence[Dict[str, object]],
) -> str:
    """Build a human-readable Markdown report for one setup-signal backtest run."""

    lines = [
        f"# Setup Signal Backtest Execution Report: {adapter.evaluator_id}",
        "",
        "## Scenario",
        "",
        (
            f"This isolated component backtest evaluates `{adapter.evaluator_id}` setup signals "
            "directly against forward price outcomes. It tests whether qualifying signals have "
            "predictive or economic value before adding portfolio sizing, settlement, fees, "
            "slippage, taxes, or overlapping-position constraints."
        ),
        "",
        "The run compares close-entry signal behavior and limit-entry trade-plan behavior against "
        f"`{config.benchmark_ticker}` and equal-weight exposure to the evaluated ticker set.",
        "",
        "## Configuration",
        "",
        markdown_table(
            ["Setting", "Value"],
            [
                ("Evaluator", run_config["evaluator_id"]),
                ("Scenario", run_config["scenario_slug"]),
                ("Run timestamp", run_config["run_timestamp"] or "N/A"),
                ("Config hash", run_config["config_hash"]),
                ("Tickers", run_config["tickers"]),
                ("Date range", f"{run_config['start_date']} to {run_config['end_date']}"),
                ("Frequency", run_config["frequency"]),
                ("Horizons", run_config["horizons"]),
                ("Benchmark", run_config["benchmark_ticker"]),
                ("Minimum setup score", run_config["min_setup_score"] or "N/A"),
                ("Minimum evidence score", run_config["min_evidence_score"] or "N/A"),
                ("Entry actions", run_config["entry_actions"]),
                ("Output directory", run_config["output_dir"]),
            ],
        ),
        "",
        "## Run Size",
        "",
        markdown_table(
            ["Metric", "Value"],
            [
                ("Predictions", len(predictions)),
                ("Outcomes", len(outcomes)),
                ("Summary rows", len(summaries)),
                ("Unique evaluation dates", len({row["evaluation_date"] for row in predictions})),
                ("Unique tickers", len({row["ticker"] for row in predictions})),
            ],
        ),
        "",
        "## Action Mix",
        "",
        markdown_table(["Action", "Predictions"], count_rows(predictions, "action")),
        "",
        "## Headline Results",
        "",
        headline_results_table(summaries),
        "",
        "## Notable Insights",
        "",
    ]
    lines.extend(f"- {item}" for item in report_insights(predictions, outcomes, summaries))
    lines.extend(
        [
            "",
            "## Ideas To Try Next",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in next_experiment_ideas(config, summaries))
    lines.extend(
        [
            "",
            "## Artifact Index",
            "",
            "- `run_config.csv` records the exact run configuration.",
            "- `predictions.csv` records point-in-time normalized setup signals.",
            "- `predictions.html` records a human-readable prediction table with setup charts.",
            "- `outcomes.csv` records entry-mode outcomes and first-exit realized P&L.",
            "- `summary.csv` records grouped machine-readable metrics.",
            "- `execution-report.md` records this human-readable run interpretation.",
            "",
        ]
    )
    return "\n".join(lines)


def build_predictions_html(
    predictions: Sequence[Dict[str, object]],
    feature_rows: Dict[str, List[Dict[str, str]]],
) -> str:
    """Build an HTML prediction table with one inline setup chart per row."""

    rows = []
    for prediction in predictions:
        ticker = str(prediction["ticker"])
        chart = prediction_svg(prediction, feature_rows.get(ticker, []))
        rows.append(
            "<tr>"
            f"<td class=\"chart\">{chart}</td>"
            f"<td>{escape(ticker)}</td>"
            f"<td>{escape(prediction['evaluation_date'])}</td>"
            f"<td>{escape(prediction['action'])}</td>"
            f"<td>{escape(prediction.get('setup_score', ''))}</td>"
            f"<td>{escape(prediction.get('evidence_score', ''))}</td>"
            f"<td>{money(prediction.get('current_price'))}</td>"
            f"<td>{money(prediction.get('buy_limit'))}</td>"
            f"<td>{money(prediction.get('stop_loss'))}</td>"
            f"<td>{money(prediction.get('take_profit'))}</td>"
            f"<td>{escape(prediction.get('setup_status', ''))}</td>"
            "</tr>"
        )

    return "\n".join(
        [
            "<!doctype html>",
            "<html lang=\"en\">",
            "<head>",
            "<meta charset=\"utf-8\">",
            "<title>Setup Signal Predictions</title>",
            "<style>",
            "body{font-family:Arial,sans-serif;margin:24px;color:#17202a;background:#f8fafc}",
            "h1{font-size:22px;margin:0 0 14px}",
            "table{border-collapse:collapse;width:100%;background:white;font-size:13px}",
            "th,td{border:1px solid #d7dde5;padding:7px 8px;vertical-align:middle;text-align:left}",
            "th{position:sticky;top:0;background:#eef3f8;z-index:1}",
            "td.chart{width:360px;padding:4px}",
            "td.chart svg{width:360px;height:auto;display:block}",
            ".muted{color:#687385;font-size:12px;margin-bottom:16px}",
            "</style>",
            "</head>",
            "<body>",
            "<h1>Setup Signal Predictions</h1>",
            "<div class=\"muted\">Each row shows the point-in-time signal plus a compact adjusted-close chart ending at the evaluation date. Lines mark buy limit, stop loss, and take profit when available.</div>",
            "<table>",
            "<thead><tr><th>Visualization</th><th>Ticker</th><th>Date</th><th>Action</th><th>Setup Score</th><th>Evidence Score</th><th>Current</th><th>Buy Limit</th><th>Stop</th><th>Take Profit</th><th>Setup Status</th></tr></thead>",
            "<tbody>",
            "\n".join(rows),
            "</tbody>",
            "</table>",
            "</body>",
            "</html>",
            "",
        ]
    )


def prediction_svg(prediction: Dict[str, object], rows: Sequence[Dict[str, str]], days: int = 90) -> str:
    return setup_visualizer().render_setup_svg_from_cells(
        prediction_setup_cells(prediction),
        raw="",
        feature_rows=list(rows),
        days=days,
        end_date=str(prediction["evaluation_date"]),
    )


def prediction_setup_cells(prediction: Dict[str, object]) -> Dict[str, str]:
    return {
        "Ticker": str(prediction.get("ticker", "")),
        "Current Price": money(prediction.get("current_price")),
        "Setup Type": str(prediction.get("setup_type", "")),
        "Key Support": money(prediction.get("key_support")),
        "Key Resistance": money(prediction.get("key_resistance")),
        "Analyst Support": "",
        "Buy Limit Order": buy_limit_text(prediction.get("buy_limit")),
        "Trailing Stop": trailing_stop_text(prediction.get("stop_loss")),
        "Take Profit": take_profit_text(prediction.get("take_profit")),
        "Reward/Risk": "" if prediction.get("reward_risk") in ("", None) else str(prediction.get("reward_risk")),
        "Setup Status": str(prediction.get("setup_status", "")),
        "Setup Score": str(prediction.get("setup_score", "")),
        "Setup Score Breakdown": "",
        "Evidence Score": str(prediction.get("evidence_score", "")),
        "Evidence Score Breakdown": "",
    }


def buy_limit_text(value: object) -> str:
    rendered = money(value)
    return f"Place buy limit at {rendered}" if rendered else ""


def trailing_stop_text(stop_loss: object) -> str:
    rendered = money(stop_loss)
    return f"Initial invalidation below {rendered}" if rendered else ""


def take_profit_text(value: object) -> str:
    rendered = money(value)
    return f"Take profit at {rendered}" if rendered else ""


def setup_visualizer():
    global SETUP_VISUALIZER
    if SETUP_VISUALIZER is None:
        spec = importlib.util.spec_from_file_location("setup_visualizer", SETUP_VISUALIZER_PATH)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        SETUP_VISUALIZER = module
    return SETUP_VISUALIZER


def headline_results_table(summaries: Sequence[Dict[str, object]]) -> str:
    rows = []
    for row in summaries:
        if row["group_type"] != "action":
            continue
        if row["group"] not in (ACTION_BUY, ACTION_WAIT, ACTION_AVOID):
            continue
        rows.append(
            (
                row["entry_mode"],
                row["horizon_days"],
                row["group"],
                row["count"],
                row["entered_count"],
                pct(row["win_rate"]),
                pct(row["average_realized_return"]),
                pct(row["average_benchmark_forward_return"]),
                pct(row["average_universe_equal_weight_forward_return"]),
                pct(row["take_profit_rate"]),
                pct(row["stop_loss_rate"]),
            )
        )
    if not rows:
        return "No action-level summary rows were generated."
    return markdown_table(
        [
            "Entry Mode",
            "Horizon",
            "Action",
            "Signals",
            "Entered",
            "Win Rate",
            "Avg Realized",
            "Avg Benchmark",
            "Avg Universe",
            "TP Rate",
            "Stop Rate",
        ],
        rows,
    )


def report_insights(
    predictions: Sequence[Dict[str, object]],
    outcomes: Sequence[Dict[str, object]],
    summaries: Sequence[Dict[str, object]],
) -> List[str]:
    insights = []
    action_counts = dict(count_rows(predictions, "action"))
    buy_count = int(action_counts.get(ACTION_BUY, 0))
    total_predictions = len(predictions)
    if total_predictions:
        insights.append(
            f"`buy` signals represented {pct(buy_count / total_predictions)} of predictions "
            f"({buy_count} of {total_predictions})."
        )

    best_buy = best_action_summary(summaries, ACTION_BUY)
    if best_buy is not None:
        insights.append(
            "Best `buy` result was "
            f"{pct(best_buy['average_realized_return'])} average realized return for "
            f"`{best_buy['entry_mode']}` at {best_buy['horizon_days']} trading days."
        )

    weakest_buy = weakest_action_summary(summaries, ACTION_BUY)
    if weakest_buy is not None:
        insights.append(
            "Weakest `buy` result was "
            f"{pct(weakest_buy['average_realized_return'])} average realized return for "
            f"`{weakest_buy['entry_mode']}` at {weakest_buy['horizon_days']} trading days."
        )

    best_relative = best_benchmark_relative_summary(summaries, ACTION_BUY)
    if best_relative is not None:
        diff = numeric(best_relative["average_realized_return"]) - numeric(
            best_relative["average_benchmark_forward_return"]
        )
        insights.append(
            "Largest `buy` edge versus benchmark was "
            f"{pct(diff)} for `{best_relative['entry_mode']}` at "
            f"{best_relative['horizon_days']} trading days."
        )

    limit_rows = [
        row
        for row in summaries
        if row["group_type"] == "action" and row["group"] == ACTION_BUY and row["entry_mode"] == "limit_entry"
    ]
    if limit_rows:
        lowest_trigger = min(limit_rows, key=lambda row: entered_rate(row))
        insights.append(
            "Lowest limit-entry trigger rate was "
            f"{pct(entered_rate(lowest_trigger))} at {lowest_trigger['horizon_days']} trading days, "
            "which helps separate signal quality from trade-plan reachability."
        )

    stop_rows = [row for row in limit_rows + [
        row
        for row in summaries
        if row["group_type"] == "action" and row["group"] == ACTION_BUY and row["entry_mode"] == "close_entry"
    ] if row["entered_count"]]
    if stop_rows:
        highest_stop = max(stop_rows, key=lambda row: numeric(row["stop_loss_rate"]))
        insights.append(
            "Highest stop-loss rate among entered `buy` groups was "
            f"{pct(highest_stop['stop_loss_rate'])} for `{highest_stop['entry_mode']}` at "
            f"{highest_stop['horizon_days']} trading days."
        )

    if not insights:
        insights.append("No entered trades were available for insight generation in this run.")
    return insights


def next_experiment_ideas(config: BacktestConfig, summaries: Sequence[Dict[str, object]]) -> List[str]:
    ideas = [
        "Run a threshold sweep across several `min_setup_score` and `min_evidence_score` values.",
        "Repeat the same configuration across longer and more varied market windows.",
        "Compare results against a random-signal or shuffled-date baseline.",
        "Add a next-open or next-close entry mode to reduce same-close timing assumptions.",
        "Test a trailing-stop outcome model instead of only initial stop and take-profit exits.",
    ]
    if len(config.tickers) < 30:
        ideas.append("Run on a larger non-curated universe to reduce ticker concentration risk.")
    if max(config.horizons) < 60:
        ideas.append("Add 40- and 60-trading-day horizons to test slower swing outcomes.")
    if not any(row["entry_mode"] == "limit_entry" and row["entered_count"] for row in summaries):
        ideas.append("Inspect buy-limit distance rules because no limit-entry trades were triggered.")
    return ideas


def best_action_summary(summaries: Sequence[Dict[str, object]], action: str) -> Optional[Dict[str, object]]:
    rows = action_rows_with_returns(summaries, action)
    return max(rows, key=lambda row: numeric(row["average_realized_return"])) if rows else None


def weakest_action_summary(summaries: Sequence[Dict[str, object]], action: str) -> Optional[Dict[str, object]]:
    rows = action_rows_with_returns(summaries, action)
    return min(rows, key=lambda row: numeric(row["average_realized_return"])) if rows else None


def best_benchmark_relative_summary(
    summaries: Sequence[Dict[str, object]],
    action: str,
) -> Optional[Dict[str, object]]:
    rows = [
        row
        for row in action_rows_with_returns(summaries, action)
        if isinstance(row["average_benchmark_forward_return"], (int, float))
    ]
    if not rows:
        return None
    return max(
        rows,
        key=lambda row: numeric(row["average_realized_return"]) - numeric(row["average_benchmark_forward_return"]),
    )


def action_rows_with_returns(summaries: Sequence[Dict[str, object]], action: str) -> List[Dict[str, object]]:
    return [
        row
        for row in summaries
        if row["group_type"] == "action"
        and row["group"] == action
        and row["entered_count"]
        and isinstance(row["average_realized_return"], (int, float))
    ]


def entered_rate(row: Dict[str, object]) -> float:
    count = numeric(row["count"])
    if count <= 0:
        return 0.0
    return numeric(row["entered_count"]) / count


def count_rows(rows: Sequence[Dict[str, object]], field: str) -> List[Tuple[object, int]]:
    counts: Dict[object, int] = {}
    for row in rows:
        value = row.get(field, "")
        counts[value] = counts.get(value, 0) + 1
    return sorted(counts.items(), key=lambda item: str(item[0]))


def markdown_table(headers: Sequence[str], rows: Sequence[Sequence[object]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(markdown_cell(value) for value in row) + " |")
    return "\n".join(lines)


def markdown_cell(value: object) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def escape(value: object) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def money(value: object) -> str:
    number = to_float(value)
    if number is None:
        return ""
    return f"${number:.2f}"


def pct(value: object) -> str:
    if not isinstance(value, (int, float)):
        return "N/A"
    return f"{value * 100:.2f}%"


def numeric(value: object) -> float:
    return float(value) if isinstance(value, (int, float)) else 0.0


def rows_through_date(rows: Sequence[Dict[str, str]], evaluation_date: str) -> List[Dict[str, str]]:
    return [row for row in rows if row["date"] <= evaluation_date]


def index_for_date(rows: Sequence[Dict[str, str]], date: str) -> Optional[int]:
    for index, row in enumerate(rows):
        if row["date"] == date:
            return index
    return None


def first_hit(
    rows: Sequence[Dict[str, str]],
    field: str,
    threshold: Optional[float],
    above: bool,
) -> Optional[int]:
    if threshold is None:
        return None
    for index, row in enumerate(rows, start=1):
        value = to_float(row.get(field))
        if value is None:
            continue
        if above and value >= threshold:
            return index
        if not above and value <= threshold:
            return index
    return None


def first_exit(take_profit_hit_at: Optional[int], stop_loss_hit_at: Optional[int]) -> str:
    if take_profit_hit_at is None and stop_loss_hit_at is None:
        return ""
    if take_profit_hit_at is None:
        return "stop_loss"
    if stop_loss_hit_at is None:
        return "take_profit"
    if stop_loss_hit_at <= take_profit_hit_at:
        return "stop_loss"
    return "take_profit"


def first_exit_offset(take_profit_hit_at: Optional[int], stop_loss_hit_at: Optional[int]) -> Optional[int]:
    if take_profit_hit_at is None:
        return stop_loss_hit_at
    if stop_loss_hit_at is None:
        return take_profit_hit_at
    return min(take_profit_hit_at, stop_loss_hit_at)


def benchmark_return(rows: Sequence[Dict[str, str]], evaluation_date: str, horizon: int) -> object:
    start_index = last_index_on_or_before(rows, evaluation_date)
    if start_index is None:
        return ""
    future_index = start_index + horizon
    if future_index >= len(rows):
        return ""
    return return_from(to_float(rows[start_index].get("adj_close")), to_float(rows[future_index].get("adj_close")))


def last_index_on_or_before(rows: Sequence[Dict[str, str]], date: str) -> Optional[int]:
    result = None
    for index, row in enumerate(rows):
        if row["date"] <= date:
            result = index
        else:
            break
    return result


def score_bucket(score: float) -> str:
    if score >= 90:
        return "90_100"
    if score >= 80:
        return "80_89"
    if score >= 70:
        return "70_79"
    if score >= 60:
        return "60_69"
    return "below_60"


def numeric_values(rows: Sequence[Dict[str, object]], field: str) -> List[float]:
    values = []
    for row in rows:
        value = row.get(field)
        if isinstance(value, (int, float)):
            values.append(float(value))
    return values


def ratio(numerator: int, denominator: int) -> object:
    if denominator == 0:
        return ""
    return numerator / denominator


def mean_or_blank(values: Sequence[float]) -> object:
    return statistics.mean(values) if values else ""


def median_or_blank(values: Sequence[float]) -> object:
    return statistics.median(values) if values else ""


def return_from(entry_price: Optional[float], exit_price: Optional[float]) -> object:
    if entry_price is None or exit_price is None or entry_price <= 0:
        return ""
    return exit_price / entry_price - 1.0


def favorable_excursion(entry_price: Optional[float], high_price: Optional[float]) -> object:
    value = return_from(entry_price, high_price)
    if not isinstance(value, float):
        return value
    return max(0.0, value)


def adverse_excursion(entry_price: Optional[float], low_price: Optional[float]) -> object:
    value = return_from(entry_price, low_price)
    if not isinstance(value, float):
        return value
    return min(0.0, value)


def to_float(value: object) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_date(value: str) -> dt.date:
    return dt.date.fromisoformat(value)


def write_csv(path: Path, fieldnames: Sequence[str], rows: Sequence[Dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
