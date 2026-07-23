import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    ROOT / "scripts/backtests/strategies/classic_12_1_momentum_rotation.py"
)
SPEC = importlib.util.spec_from_file_location("classic_rotation", str(MODULE_PATH))
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def tape(rows):
    return {
        "rows": rows,
        "dates": [row[0] for row in rows],
        "index": {row[0]: index for index, row in enumerate(rows)},
    }


def test_sale_proceeds_are_unavailable_until_settlement():
    tapes = {
        "OLD": tape([
            ("2026-01-30", 100.0, 100.0),
            ("2026-02-02", 100.0, 100.0),
            ("2026-02-03", 100.0, 100.0),
        ]),
        "NEW": tape([
            ("2026-01-30", 50.0, 50.0),
            ("2026-02-02", 50.0, 50.0),
            ("2026-02-03", 50.0, 50.0),
        ]),
    }
    trades = []
    cash, positions, settlement = MODULE.execute_sale_stage(
        "2026-01-30", "2026-02-02", "2026-02-03", ["NEW"], 0.0,
        {"OLD": 10.0}, tapes, 0.0, 0.0, trades,
    )
    assert cash == 0.0
    assert positions == {}
    assert [row["side"] for row in trades] == ["SELL"]
    assert settlement["sale_proceeds"] == 1000.0

    cash, positions = MODULE.execute_settlement_stage(
        settlement, cash, positions, tapes, 0.0, 0.0, trades,
    )
    assert cash == 0.0
    assert positions == {"NEW": 20.0}
    assert [row["side"] for row in trades] == ["SELL", "BUY"]


def test_monthly_cutoffs_use_last_completed_session():
    spy = tape([
        ("2026-01-29", 1.0, 1.0),
        ("2026-01-30", 1.0, 1.0),
        ("2026-02-02", 1.0, 1.0),
        ("2026-02-27", 1.0, 1.0),
    ])
    assert MODULE.monthly_cutoffs(
        spy, "2026-01-01", "2026-02-28"
    ) == ["2026-01-30", "2026-02-27"]


def test_spy_benchmark_stays_in_cash_until_first_execution():
    spy = tape([
        ("2026-01-29", 100.0, 100.0),
        ("2026-01-30", 100.0, 100.0),
        ("2026-02-02", 110.0, 110.0),
        ("2026-02-03", 121.0, 121.0),
    ])
    path = MODULE.benchmark_path(
        spy, spy, ["2026-01-30"], "2026-01-29", "2026-02-03"
    )
    assert path == [
        ("2026-02-02", 5000.0),
        ("2026-02-03", 5500.0),
    ]


def test_later_inception_benchmark_has_no_synthetic_prelaunch_cash():
    calendar = tape([
        ("2026-01-30", 100.0, 100.0),
        ("2026-02-02", 100.0, 100.0),
        ("2026-02-03", 100.0, 100.0),
        ("2026-02-04", 100.0, 100.0),
    ])
    later = tape([
        ("2026-02-03", 50.0, 50.0),
        ("2026-02-04", 50.0, 55.0),
    ])
    assert MODULE.benchmark_path(
        calendar, later, ["2026-01-30"], "2026-01-30", "2026-02-04"
    ) == [
        ("2026-02-03", 5000.0),
        ("2026-02-04", 5500.0),
    ]


def test_ticker_contributions_reconcile_portfolio_profit():
    tapes = {
        "A": tape([("2026-01-31", 10.0, 12.0)]),
        "B": tape([("2026-01-31", 20.0, 18.0)]),
    }
    trades = [
        {
            "ticker": "A", "side": "BUY", "gross_value": 100.0, "fee": 1.0,
        },
        {
            "ticker": "B", "side": "BUY", "gross_value": 100.0, "fee": 1.0,
        },
    ]
    rows = MODULE.ticker_profit_concentration(
        trades, {"A": 10.0, "B": 5.0}, tapes, "2026-01-31"
    )
    values = {row["ticker"]: row["profit_contribution"] for row in rows}
    assert values == {"A": 19.0, "B": -11.0}
    assert sum(values.values()) == 8.0


def test_rolling_excess_uses_twelve_month_end_intervals():
    strategy = []
    benchmark = []
    for month in range(1, 14):
        year = 2025 if month <= 12 else 2026
        calendar_month = month if month <= 12 else 1
        date = "{:04d}-{:02d}-28".format(year, calendar_month)
        strategy.append((date, 100.0 + month * 10.0))
        benchmark.append((date, 100.0 + month * 5.0))
    rows = MODULE.rolling_excess(strategy, benchmark, "benchmark")
    assert len(rows) == 1
    assert rows[0]["benchmark"] == "benchmark"
    assert rows[0]["excess_return"] > 0
