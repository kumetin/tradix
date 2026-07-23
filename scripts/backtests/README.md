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
| Configuration intent | `Configuration Intent` section. |
| Scenario bindings | Universe, [selection model](../../stages/OPERATIONS.md#selection-and-selection-models), [trigger](../../stages/OPERATIONS.md#trigger), [funding](../../stages/OPERATIONS.md#funding-profiles), [portfolio policy](../../stages/OPERATIONS.md#portfolio-transitions-and-portfolio-policies), execution model, and [evaluation](../../stages/OPERATIONS.md#evaluation-plans) sections. |
| Baselines | `Benchmarks` section. |

Strategy backtests orient final results around the complete strategy
configuration. All strategies follow the canonical pipeline in
[`strategies/README.md`](../../strategies/README.md); backtests bind its concrete
stage descriptors and configuration profiles without referencing a separate
flow file. Research hypotheses,
success criteria, run indexes, and decisions live under
[`experiments/`](../../experiments/README.md). The root driver resolves and
validates every strategy specification. It also executes the registered
`technical-resistance-runner/tc-001-random-50-universe-1-monthly` and
`technical-resistance-runner/tc-002-random-50-universe-1-sma50-exit`
portfolio backtests, plus the
`technical-resistance-runner/tc-003-pre-2014-sma50-robustness` two-window
comparison; other strategy specifications remain validate-only until compatible
drivers are registered.

The registered
`regime-gated-technical-resistance/tc-001-eight-dataset-robustness` driver runs
the frozen universe-1 candidate configuration with its declared SMA200 gate, 15%
stop, and fixed research costs. The remaining seven replications are preserved
as separately labeled artifacts.

## Isolated Component Backtests

Expected spec location:

```text
backtests/components/<component-type>/<backtest-id>.md
```

Required inputs:

| Requirement | Source |
| --- | --- |
| Component type/descriptor | `Component Under Test` or `Applicable Component Type` section. |
| Backtest type | `Backtest Type` = `isolated component backtest`. |
| Direct contract | `Direct Input/Output Contract` section. |
| Metrics and outputs | `Metrics` and `Output Location` sections. |

The executable isolated component driver supports the
[`classic-12-1-momentum`](../../stages/selection-models/classic-12-1-momentum.md)
historical-membership benchmark, the
[`fundamental-technical-momentum`](../../stages/selection-models/fundamental-technical-momentum.md)
selection benchmark, its condition-count and volume diagnostics, the
seven-condition validation, the
[`continuous-fundamental-momentum`](../../stages/selection-models/continuous-fundamental-momentum.md)
validation, the
[`partial-profit-breakeven-time-exit`](../../stages/portfolio-policies/partial-profit-breakeven-time-exit.md)
portfolio-policy trade-path benchmark, and [setup evaluators](../../stages/OPERATIONS.md#setup-evaluators) that
emit normalized `SetupSignal` records. Evaluator-specific adapters live under:

```text
scripts/backtests/setup_evaluator_adapters/
```

Each adapter should translate its evaluator's native output into the generic
`SetupSignal` interface and delegate execution to
`scripts/backtests/setup_evaluator_forward_outcome_benchmark.py`.

Each forward-outcome benchmark run writes machine-readable CSV artifacts plus
`predictions.html`, a human-readable prediction table with inline setup charts,
and `execution-report.md`, a human-readable execution report that summarizes
the scenario, configuration, key results, generated insights, and next
experiments to try. The setup charts in `predictions.html` are rendered through
`scripts/setup-visualizer/setup_visualizer.py` so watchlist and backtest
visualizations share the same chart logic.

When `--output-dir` is omitted, the driver creates a run directory under:

```text
artifacts/stock/backtests/components/setup-evaluators/setup-evaluator-forward-outcome-benchmark/
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
  backtests/components/setup-evaluators/setup-evaluator-forward-outcome-benchmark.md \
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
