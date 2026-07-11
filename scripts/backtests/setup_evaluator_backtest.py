#!/usr/bin/env python3
"""Generic point-in-time backtest engine for setup-evaluator signals.

Evaluator-specific code should adapt its native output to ``SetupSignal`` and
then call ``run_setup_evaluator_backtest(...)``. The engine handles local
feature loading, evaluation-date selection, point-in-time row slicing, entry
simulation, first-exit realized P&L, benchmark returns, summaries, and CSV
output.
"""

from __future__ import annotations

import csv
import datetime as dt
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


ROOT = Path(__file__).resolve().parents[2]
FEATURE_ROOT = ROOT / "data/stock/features/daily"

ACTION_BUY = "buy"
ACTION_WAIT = "wait"
ACTION_AVOID = "avoid"

PREDICTION_BASE_FIELDS = [
    "prediction_id",
    "evaluator_id",
    "evaluation_date",
    "ticker",
    "action",
    "rank",
    "score",
    "confidence",
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
    "tickers",
    "start_date",
    "end_date",
    "frequency",
    "horizons",
    "benchmark_ticker",
    "min_score",
    "min_confidence",
    "entry_actions",
]


@dataclass(frozen=True)
class SetupSignal:
    evaluator_id: str
    ticker: str
    evaluation_date: str
    action: str
    score: Optional[float]
    confidence: Optional[float]
    current_price: Optional[float]
    entry_price: Optional[float]
    buy_limit: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    rank: Optional[int] = None
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
    min_score: Optional[float] = None
    min_confidence: Optional[float] = None
    entry_actions: Sequence[str] = (ACTION_BUY,)


class SetupEvaluatorAdapter:
    evaluator_id = ""
    extra_prediction_fields: Sequence[str] = ()
    summary_group_fields: Sequence[str] = ("action", "rank", "score", "confidence")

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
    write_csv(config.output_dir / "outcomes.csv", OUTCOME_FIELDS, outcomes)
    write_csv(config.output_dir / "summary.csv", SUMMARY_FIELDS, summaries)
    write_csv(config.output_dir / "run_config.csv", RUN_CONFIG_FIELDS, [run_config_row(adapter, config)])

    print(f"Wrote {len(predictions)} predictions to {config.output_dir / 'predictions.csv'}")
    print(f"Wrote {len(outcomes)} outcomes to {config.output_dir / 'outcomes.csv'}")
    print(f"Wrote {len(summaries)} summary rows to {config.output_dir / 'summary.csv'}")
    print(f"Wrote run config to {config.output_dir / 'run_config.csv'}")


def run_config_row(adapter: SetupEvaluatorAdapter, config: BacktestConfig) -> Dict[str, object]:
    return {
        "evaluator_id": adapter.evaluator_id,
        "tickers": " ".join(config.tickers),
        "start_date": config.start_date.isoformat(),
        "end_date": config.end_date.isoformat(),
        "frequency": config.frequency,
        "horizons": " ".join(str(value) for value in config.horizons),
        "benchmark_ticker": config.benchmark_ticker,
        "min_score": "" if config.min_score is None else config.min_score,
        "min_confidence": "" if config.min_confidence is None else config.min_confidence,
        "entry_actions": " ".join(config.entry_actions),
    }


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
        "rank": signal.rank,
        "score": signal.score,
        "confidence": signal.confidence,
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
    if config.min_score is not None and (signal.score is None or signal.score < config.min_score):
        return False
    if config.min_confidence is not None and (
        signal.confidence is None or signal.confidence < config.min_confidence
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
        if field_name == "rank":
            groups.append((field_name, rank_bucket(int(value))))
        elif field_name in ("score", "confidence"):
            groups.append((field_name, score_bucket(float(value))))
        else:
            groups.append((field_name, str(value)))
    return groups


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


def rank_bucket(rank: int) -> str:
    if rank <= 5:
        return "rank_1_5"
    if rank <= 10:
        return "rank_6_10"
    if rank <= 20:
        return "rank_11_20"
    return "rank_21_plus"


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
