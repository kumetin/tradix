#!/usr/bin/env python3
"""Behavioral tests for the pure partial-profit portfolio-policy function."""

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "stages/portfolio-policies/partial_profit_breakeven_time_exit.py"
SPEC = importlib.util.spec_from_file_location("partial_profit_breakeven_time_exit", MODULE_PATH)
policy = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = policy
SPEC.loader.exec_module(policy)


def lot(**changes):
    value = {
        "instrument_id": "AAA",
        "entry_price": 100,
        "original_quantity": 10,
        "remaining_quantity": 10,
        "partial_profit_filled": False,
    }
    value.update(changes)
    return value


def run_policy(position, bar, sessions):
    return policy.transition(
        as_of="2026-07-22",
        selection_intent=[],
        portfolio_state=[position],
        cash_state={"settled": 100},
        daily_market_state={"AAA": bar},
        session_index={"AAA": sessions},
    )


class PartialProfitBreakevenTimeExitTest(unittest.TestCase):
    def test_places_initial_stop_and_partial_limit(self):
        result = run_policy(lot(), {"open": 101, "high": 110, "low": 99, "close": 105}, 4)

        self.assertEqual(["initial_stop", "partial_profit"], [order["reason"] for order in result.orders])
        self.assertEqual(92.5, result.orders[0]["stop_price"])
        self.assertAlmostEqual(122.5, result.orders[1]["limit_price"])
        self.assertEqual(5, result.orders[1]["quantity"])

    def test_ambiguous_bar_stops_first_and_models_gap(self):
        result = run_policy(lot(), {"open": 90, "high": 125, "low": 89, "close": 120}, 4)

        self.assertEqual(1, len(result.orders))
        self.assertEqual("initial_stop", result.orders[0]["reason"])
        self.assertEqual(90, result.orders[0]["expected_fill_price"])
        self.assertEqual("ambiguous_bar_stop_first", result.constraint_events[0]["reason"])

    def test_partial_fill_activates_breakeven_stop(self):
        result = run_policy(
            lot(remaining_quantity=5, partial_profit_filled=True),
            {"open": 101, "high": 108, "low": 99, "close": 104},
            20,
        )

        self.assertEqual(("breakeven_stop",), tuple(order["reason"] for order in result.orders))
        self.assertEqual(100, result.orders[0]["stop_price"])

    def test_stagnation_and_horizon_exits(self):
        stagnant = run_policy(lot(), {"open": 101, "high": 102, "low": 98, "close": 100}, 15)
        expired = run_policy(lot(), {"open": 150, "high": 151, "low": 149, "close": 150}, 378)

        self.assertEqual("stagnation_exit", stagnant.orders[0]["reason"])
        self.assertEqual("maximum_holding_exit", expired.orders[0]["reason"])

    def test_allocates_settled_cash_by_target_weight(self):
        result = policy.transition(
            as_of="2026-07-22",
            selection_intent=[
                {"instrument_id": "AAA", "weight": 0.6},
                {"instrument_id": "BBB", "weight": 0.4},
            ],
            portfolio_state=[],
            cash_state={"settled": 1000},
            daily_market_state={},
            session_index={},
        )

        self.assertEqual([600, 400], [order["notional"] for order in result.orders])
        self.assertEqual({"amount": 0.0, "reason": "fully_allocated"}, result.unallocated_cash)

    def test_missing_bar_retains_and_reports(self):
        result = run_policy(lot(), {}, 4)

        self.assertFalse(result.orders)
        self.assertEqual("missing_daily_bar", result.retained_positions[0]["reason"])
        self.assertEqual("missing_daily_bar", result.constraint_events[0]["reason"])


if __name__ == "__main__":
    unittest.main()
