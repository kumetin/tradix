# Tests

This directory defines tests for platform components.

Component tests should focus on modules with meaningful behavior:

- `selection-models/`
- `portfolio-policies/`
- `execution-models/`

Static profile directories such as `universes/` and `funding-profiles/` usually need
validation checks rather than full behavioral tests.

## Test Types

| Test Type | Purpose |
| --- | --- |
| Component behavior | Verify that a component satisfies its contract in isolation. |
| Component backtest | Compare one component profile or parameter family under a fixed harness. |
| Integration backtest | Verify that a configured backtest works end to end. |
| Static validation | Verify that profile files are internally consistent. |

## Scoring

Component tests are not ranked primarily by profit. They are ranked by whether
the component fulfills its contract without introducing unwanted side effects
such as excess turnover, cash drag, settlement leakage, or look-ahead bias.

Component backtests may compare performance, but only after the component's
fixed harness, baselines, evaluation windows, and interpretation rules are
declared under `backtests/components/`.

## Current Test Specs

- [IBKR Cash T+1](execution-models/ibkr-cash-t-plus-one.md)
- [Single Position Rotation](portfolio-policies/single-position-rotation.md)
- [Multi Position Target Weight Rotation](portfolio-policies/multi-position-target-weight-rotation.md)
- [SMA Drawdown Trailing Return](selection-models/sma-drawdown-trailing-return.md)
- [Static Profile Validation](validation/static-profiles.md)

## Executable Checks

Run the complete executable Python test suite from the repository root:

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
```

The executable suites currently cover:

- root backtest spec resolution and driver-argument forwarding
- lower-risk swing-entry construction and scoring
- the lower-risk swing-entry backtest adapter
- generic setup-evaluator backtest dates, entries, exits, benchmarks, reports,
  visualizations, and run hashing
- stock-price provider normalization into the canonical CSV schema
- canonical inventory fast-path checks and missing-row detection

From the repository root, run static profile validation:

```sh
python3 tests/validation/validate_static_profiles.py
```

If your shell is already inside `tests/`, run:

```sh
python3 validation/validate_static_profiles.py
```

Run one test module directly when isolating a failure, for example:

```sh
python3 tests/test_lower_risk_swing_entry_evaluator.py
```

Or from inside `tests/`:

```sh
python3 test_lower_risk_swing_entry_evaluator.py
```
