# Backtest Drivers

Use `run_backtest.py` as the single entry point for backtest execution:

```sh
python3 scripts/backtests/run_backtest.py BACKTEST_SPEC.md -- DRIVER_ARGS...
```

The root driver resolves the markdown spec, validates required sections and
links, classifies the backtest type, and delegates to the matching driver.

## Strategy Backtests

Expected spec location:

```text
backtests/strategies/<strategy-id>/<test-id>.md
```

Required inputs:

| Requirement | Source |
| --- | --- |
| Strategy definition | `Strategy:` link in the spec. |
| Strategy flow | `Strategy Flow:` link in the spec. |
| Test hypothesis | `Edge Being Tested` section. |
| Run profiles | Universe, selection model, trigger, funding, portfolio policy, execution model, and evaluation sections. |
| Baselines | `Benchmarks` section. |

Strategy backtests orient final results around the complete strategy
configuration. The root driver can resolve and validate these specs, but a
portfolio-level simulation engine is not registered yet.

## Isolated Component Backtests

Expected spec location:

```text
backtests/components/<component-type>/<backtest-id>.md
```

Required inputs:

| Requirement | Source |
| --- | --- |
| Component type/profile | `Component Under Test` section. |
| Backtest type | `Backtest Type` = `isolated component backtest`. |
| Direct contract | `Direct Input/Output Contract` section. |
| Metrics and outputs | `Metrics` and `Output Location` sections. |

The current executable isolated component driver supports setup evaluators that emit
normalized `SetupSignal` records. Example:

```sh
python3 scripts/backtests/run_backtest.py \
  backtests/components/setup-evaluators/setup-signal-backtest.md \
  --evaluator lower-risk-swing-entry \
  -- \
  --tickers NVDA TLN ECL NEE SO AMZN XEL EXC \
  --start-date 2026-01-01 \
  --end-date 2026-03-31 \
  --frequency weekly \
  --horizons 5 10 \
  --min-score 80
```

## Harnessed Component Backtests

Expected spec location:

```text
backtests/components/<component-type>/<backtest-id>.md
```

Required inputs:

| Requirement | Source |
| --- | --- |
| Component type/profile | `Component Under Test` section. |
| Backtest type | `Backtest Type` = `harnessed component backtest`. |
| Fixed harness | `Fixed Harness` section with surrounding strategy stages. |
| Metrics and outputs | `Metrics` and `Output Location` sections. |

Harnessed component backtests use the same portfolio-level simulation engine as
strategy backtests. Final results should be oriented around the component under
test: incremental contribution, parameter stability, failure modes, and whether
the component should be reused.

## Result Orientation

| Backtest type | Primary result orientation |
| --- | --- |
| Strategy backtest | Whether the complete strategy configuration works end to end. |
| Harnessed component backtest | Whether the component improves or destabilizes a fixed strategy harness. |
| Isolated component backtest | Whether the component's direct outputs have predictive or economic value. |
