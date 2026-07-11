#!/usr/bin/env python3
"""Run the generic setup-signal backtest for lower-risk swing-entry signals."""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import sys
from pathlib import Path
from typing import Dict, List, Sequence


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = (
    ROOT
    / "artifacts/stock/backtests/components/setup-evaluators/setup-signal-backtest/lower-risk-swing-entry"
)
EVALUATOR_PATH = ROOT / "scripts/setup-evaluators/lower_risk_swing_entry.py"

sys.path.insert(0, str(SCRIPT_DIR))
from setup_evaluator_backtest import (  # noqa: E402
    ACTION_AVOID,
    ACTION_BUY,
    ACTION_WAIT,
    BacktestConfig,
    SetupEvaluatorAdapter,
    SetupSignal,
    parse_horizons,
    run_setup_evaluator_backtest,
)


SPEC = importlib.util.spec_from_file_location("lower_risk_swing_entry", EVALUATOR_PATH)
lower_risk_swing_entry = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = lower_risk_swing_entry
SPEC.loader.exec_module(lower_risk_swing_entry)

LowerRiskSwingEntryEvaluator = lower_risk_swing_entry.LowerRiskSwingEntryEvaluator


class LowerRiskSwingEntryAdapter(SetupEvaluatorAdapter):
    evaluator_id = "lower-risk-swing-entry"
    extra_prediction_fields = (
        "setup_status",
        "setup_type",
        "key_support",
        "key_resistance",
        "trailing_stop_amount",
        "trailing_stop_pct",
        "reward_risk",
        "rank_ep",
        "rank_sq",
        "rank_rr",
        "rank_ts",
        "rank_as",
        "rank_er",
        "confidence_pd",
        "confidence_sr",
        "confidence_ma",
        "confidence_ad",
        "confidence_tm",
        "confidence_rg",
    )
    summary_group_fields = ("action", "rank", "score", "confidence", "setup_status")

    def evaluate_batch(
        self,
        evaluation_date: str,
        point_in_time_rows_by_ticker: Dict[str, List[Dict[str, str]]],
    ) -> List[SetupSignal]:
        setups = [
            LowerRiskSwingEntryEvaluator.construct_setup(ticker, rows)
            for ticker, rows in point_in_time_rows_by_ticker.items()
        ]
        return [self.to_signal(ranked) for ranked in LowerRiskSwingEntryEvaluator.rank_setups(setups)]

    def to_signal(self, ranked: object) -> SetupSignal:
        setup = ranked.setup
        evaluation = ranked.evaluation
        action = action_from_status(evaluation.setup_status)
        return SetupSignal(
            evaluator_id=self.evaluator_id,
            ticker=setup.ticker,
            evaluation_date=setup.latest_date,
            action=action,
            rank=evaluation.rank,
            score=float(evaluation.rank_score),
            confidence=float(evaluation.confidence),
            current_price=setup.current_price,
            entry_price=setup.current_price,
            buy_limit=setup.buy_limit,
            stop_loss=setup.invalidation_level,
            take_profit=setup.take_profit,
            metadata={
                "setup_status": evaluation.setup_status,
                "setup_type": setup.setup_type,
                "key_support": setup.key_support,
                "key_resistance": setup.key_resistance,
                "trailing_stop_amount": setup.trailing_stop_amount,
                "trailing_stop_pct": setup.trailing_stop_pct,
                "reward_risk": setup.reward_risk,
                "rank_breakdown": evaluation.rank_breakdown,
                "confidence_breakdown": evaluation.confidence_breakdown,
            },
        )

    def extra_prediction_row(self, signal: SetupSignal) -> Dict[str, object]:
        rank_breakdown = signal.metadata["rank_breakdown"]
        confidence_breakdown = signal.metadata["confidence_breakdown"]
        return {
            "setup_status": signal.metadata["setup_status"],
            "setup_type": signal.metadata["setup_type"],
            "key_support": signal.metadata["key_support"],
            "key_resistance": signal.metadata["key_resistance"],
            "trailing_stop_amount": signal.metadata["trailing_stop_amount"],
            "trailing_stop_pct": signal.metadata["trailing_stop_pct"],
            "reward_risk": signal.metadata["reward_risk"],
            "rank_ep": rank_breakdown["EP"],
            "rank_sq": rank_breakdown["SQ"],
            "rank_rr": rank_breakdown["RR"],
            "rank_ts": rank_breakdown["TS"],
            "rank_as": rank_breakdown["AS"],
            "rank_er": rank_breakdown["ER"],
            "confidence_pd": confidence_breakdown["PD"],
            "confidence_sr": confidence_breakdown["SR"],
            "confidence_ma": confidence_breakdown["MA"],
            "confidence_ad": confidence_breakdown["AD"],
            "confidence_tm": confidence_breakdown["TM"],
            "confidence_rg": confidence_breakdown["RG"],
        }


def action_from_status(status: str) -> str:
    if status == lower_risk_swing_entry.STATUS_READY_NEAR_BUY_ZONE:
        return ACTION_BUY
    if status in (
        lower_risk_swing_entry.STATUS_WAIT_FOR_PULLBACK,
        lower_risk_swing_entry.STATUS_WATCH_BREAKOUT_RETEST,
    ):
        return ACTION_WAIT
    return ACTION_AVOID


def main(argv: Sequence[str] = None) -> int:
    args = parse_args(argv)
    config = BacktestConfig(
        tickers=[ticker.upper() for ticker in args.tickers],
        start_date=dt.date.fromisoformat(args.start_date),
        end_date=dt.date.fromisoformat(args.end_date),
        frequency=args.frequency,
        horizons=parse_horizons(args.horizons),
        benchmark_ticker=args.benchmark.upper(),
        output_dir=args.output_dir,
        min_score=args.min_score,
        min_confidence=args.min_confidence,
    )
    run_setup_evaluator_backtest(LowerRiskSwingEntryAdapter(), config)
    return 0


def parse_args(argv: Sequence[str] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backtest lower-risk swing-entry signals with the generic setup-signal engine."
    )
    parser.add_argument("--tickers", nargs="+", required=True)
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument(
        "--frequency",
        choices=("daily", "weekly", "monthly"),
        default="weekly",
        help="Evaluation cadence. Weekly/monthly use the last available local trading date in each period.",
    )
    parser.add_argument("--horizons", nargs="+", default=["5", "10", "20", "40", "60"])
    parser.add_argument("--benchmark", default="SPY")
    parser.add_argument("--min-score", type=float, default=None)
    parser.add_argument("--min-confidence", type=float, default=None)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.epilog = (
        "This script only adapts lower-risk swing-entry outputs into normalized "
        "SetupSignal records. Generic entry modes, first-exit P&L, summaries, "
        "and CSV writing live in setup_evaluator_backtest.py."
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
