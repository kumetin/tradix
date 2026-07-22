#!/usr/bin/env python3
"""Run a setup-signal backtest for lower-risk swing-entry signals.

Parameters:
    Required CLI options select tickers and evaluation dates. Optional settings
    control cadence, horizons, benchmark, stop model, score thresholds,
    execution mode, scenario label, and output directory.
External sources:
    Local precomputed feature CSVs plus the lower-risk evaluator and generic
    backtest engine modules in this repository.
Side effects:
    Reads point-in-time feature history, creates an artifact run directory,
    writes CSV/Markdown/HTML reports and charts, and prints run results.
Examples:
    Run a weekly two-ticker backtest::

        python3 scripts/backtests/setup_evaluator_adapters/lower_risk_swing_entry.py --tickers NVDA AMD --start-date 2025-01-01 --end-date 2025-12-31

    Test stricter evidence and an alternate stop model::

        python3 scripts/backtests/setup_evaluator_adapters/lower_risk_swing_entry.py --tickers NVDA --start-date 2025-01-01 --end-date 2025-12-31 --min-evidence-score 70 --stop-model support-atr-1.5 --horizons 10 20 40
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import sys
from pathlib import Path
from typing import Dict, List, Sequence


ROOT = Path(__file__).resolve().parents[3]
BACKTEST_SCRIPT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "artifacts/stock/backtests/components/setup-evaluators/setup-signal-backtest"
EVALUATOR_PATH = ROOT / "scripts/setup-evaluators/lower_risk_swing_entry.py"

sys.path.insert(0, str(BACKTEST_SCRIPT_DIR))
from setup_evaluator_backtest import (  # noqa: E402
    ACTION_AVOID,
    ACTION_BUY,
    ACTION_WAIT,
    BacktestConfig,
    SetupEvaluatorAdapter,
    SetupSignal,
    config_with_run_output_dir,
    parse_horizons,
    run_setup_evaluator_backtest,
)


SPEC = importlib.util.spec_from_file_location("lower_risk_swing_entry", EVALUATOR_PATH)
lower_risk_swing_entry = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = lower_risk_swing_entry
SPEC.loader.exec_module(lower_risk_swing_entry)

LowerRiskSwingEntryEvaluator = lower_risk_swing_entry.LowerRiskSwingEntryEvaluator

STOP_MODEL_CURRENT = "current"
STOP_MODEL_RISK_125 = "risk-1.25"
STOP_MODEL_RISK_150 = "risk-1.5"
STOP_MODEL_SUPPORT_ATR_120 = "support-atr-1.2"
STOP_MODEL_SUPPORT_ATR_150 = "support-atr-1.5"
STOP_MODELS = (
    STOP_MODEL_CURRENT,
    STOP_MODEL_RISK_125,
    STOP_MODEL_RISK_150,
    STOP_MODEL_SUPPORT_ATR_120,
    STOP_MODEL_SUPPORT_ATR_150,
)


class LowerRiskSwingEntryAdapter(SetupEvaluatorAdapter):
    evaluator_id = "lower-risk-swing-entry"
    extra_prediction_fields = (
        "stop_model",
        "original_stop_loss",
        "setup_status",
        "setup_type",
        "key_support",
        "key_resistance",
        "trailing_stop_amount",
        "trailing_stop_pct",
        "reward_risk",
        "setup_score_ep",
        "setup_score_sq",
        "setup_score_rr",
        "setup_score_ts",
        "setup_score_as",
        "setup_score_er",
        "evidence_score_pd",
        "evidence_score_sr",
        "evidence_score_ma",
        "evidence_score_ad",
        "evidence_score_tm",
        "evidence_score_rg",
    )
    summary_group_fields = ("action", "setup_score", "evidence_score", "setup_status")

    def __init__(self, stop_model: str = STOP_MODEL_CURRENT) -> None:
        if stop_model not in STOP_MODELS:
            raise ValueError(f"Unsupported stop model: {stop_model}")
        self.stop_model = stop_model

    def evaluate_batch(
        self,
        evaluation_date: str,
        point_in_time_rows_by_ticker: Dict[str, List[Dict[str, str]]],
    ) -> List[SetupSignal]:
        rows_by_ticker = {ticker.upper(): rows for ticker, rows in point_in_time_rows_by_ticker.items()}
        setups = [
            LowerRiskSwingEntryEvaluator.construct_setup(ticker, rows)
            for ticker, rows in rows_by_ticker.items()
        ]
        return [
            self.to_signal(scored, rows_by_ticker.get(scored.setup.ticker, []))
            for scored in LowerRiskSwingEntryEvaluator.score_setups(setups)
        ]

    def to_signal(self, scored: object, feature_rows: Sequence[Dict[str, str]] = ()) -> SetupSignal:
        setup = scored.setup
        evaluation = scored.evaluation
        action = action_from_status(evaluation.setup_status)
        stop_loss = stop_loss_for_model(setup, feature_rows, self.stop_model)
        return SetupSignal(
            evaluator_id=self.evaluator_id,
            ticker=setup.ticker,
            evaluation_date=setup.latest_date,
            action=action,
            setup_score=float(evaluation.setup_score),
            evidence_score=float(evaluation.evidence_score),
            current_price=setup.current_price,
            entry_price=setup.current_price,
            buy_limit=setup.buy_limit,
            stop_loss=stop_loss,
            take_profit=setup.take_profit,
            metadata={
                "stop_model": self.stop_model,
                "original_stop_loss": setup.invalidation_level,
                "setup_status": evaluation.setup_status,
                "setup_type": setup.setup_type,
                "key_support": setup.key_support,
                "key_resistance": setup.key_resistance,
                "trailing_stop_amount": setup.trailing_stop_amount,
                "trailing_stop_pct": setup.trailing_stop_pct,
                "reward_risk": setup.reward_risk,
                "setup_score_breakdown": evaluation.setup_score_breakdown,
                "evidence_score_breakdown": evaluation.evidence_score_breakdown,
            },
        )

    def extra_prediction_row(self, signal: SetupSignal) -> Dict[str, object]:
        setup_score_breakdown = signal.metadata["setup_score_breakdown"]
        evidence_score_breakdown = signal.metadata["evidence_score_breakdown"]
        return {
            "stop_model": signal.metadata["stop_model"],
            "original_stop_loss": signal.metadata["original_stop_loss"],
            "setup_status": signal.metadata["setup_status"],
            "setup_type": signal.metadata["setup_type"],
            "key_support": signal.metadata["key_support"],
            "key_resistance": signal.metadata["key_resistance"],
            "trailing_stop_amount": signal.metadata["trailing_stop_amount"],
            "trailing_stop_pct": signal.metadata["trailing_stop_pct"],
            "reward_risk": signal.metadata["reward_risk"],
            "setup_score_ep": setup_score_breakdown["EP"],
            "setup_score_sq": setup_score_breakdown["SQ"],
            "setup_score_rr": setup_score_breakdown["RR"],
            "setup_score_ts": setup_score_breakdown["TS"],
            "setup_score_as": setup_score_breakdown["AS"],
            "setup_score_er": setup_score_breakdown["ER"],
            "evidence_score_pd": evidence_score_breakdown["PD"],
            "evidence_score_sr": evidence_score_breakdown["SR"],
            "evidence_score_ma": evidence_score_breakdown["MA"],
            "evidence_score_ad": evidence_score_breakdown["AD"],
            "evidence_score_tm": evidence_score_breakdown["TM"],
            "evidence_score_rg": evidence_score_breakdown["RG"],
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


def stop_loss_for_model(setup: object, feature_rows: Sequence[Dict[str, str]], stop_model: str) -> object:
    """Return the execution stop-loss level for a backtest stop-model variant."""

    if stop_model == STOP_MODEL_CURRENT:
        return setup.invalidation_level
    if setup.buy_limit is None or setup.invalidation_level is None:
        return setup.invalidation_level
    current_risk = setup.buy_limit - setup.invalidation_level
    if current_risk <= 0:
        return setup.invalidation_level
    if stop_model == STOP_MODEL_RISK_125:
        return setup.buy_limit - current_risk * 1.25
    if stop_model == STOP_MODEL_RISK_150:
        return setup.buy_limit - current_risk * 1.5
    if stop_model in (STOP_MODEL_SUPPORT_ATR_120, STOP_MODEL_SUPPORT_ATR_150):
        if setup.key_support is None:
            return setup.invalidation_level
        atr = lower_risk_swing_entry.average_true_range(feature_rows, lower_risk_swing_entry.ATR_WINDOW)
        if atr is None or atr <= 0:
            return setup.invalidation_level
        multiple = 1.2 if stop_model == STOP_MODEL_SUPPORT_ATR_120 else 1.5
        return setup.key_support - atr * multiple
    raise ValueError(f"Unsupported stop model: {stop_model}")


def main(argv: Sequence[str] = None) -> int:
    args = parse_args(argv)
    adapter = LowerRiskSwingEntryAdapter(stop_model=args.stop_model)
    config = BacktestConfig(
        tickers=[ticker.upper() for ticker in args.tickers],
        start_date=dt.date.fromisoformat(args.start_date),
        end_date=dt.date.fromisoformat(args.end_date),
        frequency=args.frequency,
        horizons=parse_horizons(args.horizons),
        benchmark_ticker=args.benchmark.upper(),
        output_dir=args.output_dir or DEFAULT_OUTPUT_ROOT,
        min_setup_score=args.min_setup_score,
        min_evidence_score=args.min_evidence_score,
        run_parameters={"stop_model": args.stop_model},
        scenario_slug=args.scenario_slug,
    )
    if args.output_dir is None:
        config = config_with_run_output_dir(adapter.evaluator_id, config, DEFAULT_OUTPUT_ROOT)
    run_setup_evaluator_backtest(adapter, config)
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
    parser.add_argument("--stop-model", choices=STOP_MODELS, default=STOP_MODEL_CURRENT)
    parser.add_argument("--min-setup-score", "--min-score", dest="min_setup_score", type=float, default=None)
    parser.add_argument(
        "--min-evidence-score",
        "--min-confidence",
        dest="min_evidence_score",
        type=float,
        default=None,
    )
    parser.add_argument(
        "--scenario-slug",
        default="manual",
        help="Human-readable run label used in the default output directory name.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help=(
            "Explicit artifact directory. If omitted, a run directory is created under "
            f"{DEFAULT_OUTPUT_ROOT} using <timestamp>__<evaluator-id>__<scenario-slug>__<config-hash>."
        ),
    )
    parser.epilog = (
        "This script only adapts lower-risk swing-entry outputs into normalized "
        "SetupSignal records. Generic entry modes, first-exit P&L, summaries, "
        "and CSV writing live in setup_evaluator_backtest.py."
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
