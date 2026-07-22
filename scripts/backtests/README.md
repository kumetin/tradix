# Backtest Drivers

Use `run_backtest.py` as the single entry point for backtest [execution](../../stages/OPERATIONS.md#execution-and-execution-models):

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
| [Strategy definition](../../strategies/README.md) | `Strategy:` link in the spec. |
| Test hypothesis | `Edge Being Tested` section. |
| Run profiles | Universe, [selection model](../../stages/OPERATIONS.md#selection-and-selection-models), [trigger](../../stages/OPERATIONS.md#trigger), [funding](../../stages/OPERATIONS.md#funding-profiles), [portfolio policy](../../stages/OPERATIONS.md#portfolio-transitions-and-portfolio-policies), execution model, and [evaluation](../../stages/OPERATIONS.md#evaluation-plans) sections. |
| Baselines | `Benchmarks` section. |

Strategy backtests orient final results around the complete strategy
configuration. All strategies follow the canonical pipeline in
[`strategies/README.md`](../../strategies/README.md); backtests bind its concrete
profiles without referencing a separate flow file. The root driver can resolve and validate these specs, but a
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

The current executable isolated component driver supports [setup evaluators](../../stages/OPERATIONS.md#setup-evaluators) that
emit normalized `SetupSignal` records. Evaluator-specific adapters live under:

```text
scripts/backtests/setup_evaluator_adapters/
```

Each adapter should translate its evaluator's native output into the generic
`SetupSignal` interface and delegate execution to
`scripts/backtests/setup_evaluator_backtest.py`.

Each setup-signal run writes machine-readable CSV artifacts plus
`predictions.html`, a human-readable prediction table with inline setup charts,
and `execution-report.md`, a human-readable execution report that summarizes
the scenario, configuration, key results, generated insights, and next
experiments to try. The setup charts in `predictions.html` are rendered through
`scripts/setup-visualizer/setup_visualizer.py` so watchlist and backtest
visualizations share the same chart logic.

When `--output-dir` is omitted, the driver creates a run directory under:

```text
artifacts/stock/backtests/components/setup-evaluators/setup-signal-backtest/
```

Run directories use:

```text
<run-timestamp>__<evaluator-id>__<scenario-slug>__<config-hash>
```

The timestamp is UTC in `YYYYMMDD-HHMMSSZ` format. The config hash is derived
from evaluator, tickers, date range, cadence, horizons, benchmark, thresholds,
and entry actions.

Example:

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
  --min-setup-score 80 \
  --min-evidence-score 70 \
  --stop-model current \
  --scenario-slug nvda-utility-megacap-smoke
```

## Result Orientation

| Backtest type | Primary result orientation |
| --- | --- |
| Strategy backtest | Whether the complete strategy configuration works end to end. |
| Isolated component backtest | Whether the component's direct outputs have predictive or economic value. |

There is no harnessed component category. A comparison that requires a complete
strategy is a strategy backtest with that configuration axis varied.
