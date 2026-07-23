# Backtests

This directory contains all backtest specifications.

- `strategies/` contains executable full-strategy scenarios. Each scenario
  selects a falsifiable strategy thesis and binds stage descriptors,
  configuration profiles, and parameter values. Research hypotheses and outcomes belong under
  [`experiments/`](../experiments/README.md).
- `components/` contains independent component benchmarks. A component must
  expose a direct contract that can be compared without a complete strategy.

[Reusable strategy definitions](../strategies/README.md) live under
`strategies/`. Independently benchmarkable components and their descriptors
live together under `stages/`.
[Static universes](../stages/OPERATIONS.md#universe-resolution-and-universe-models),
[triggers](../stages/OPERATIONS.md#trigger),
[funding profiles](../stages/OPERATIONS.md#funding-profiles), and evaluations
live under [`configuration/`](../configuration/README.md); they are inputs, not
performance components. Generated backtest artifacts should live under
`artifacts/stock/backtests/`.

Run backtests through the root driver:

```sh
python3 scripts/backtests/run_backtest.py BACKTEST_SPEC.md -- DRIVER_ARGS...
```

Driver contracts are documented in
[scripts/backtests/README.md](../scripts/backtests/README.md).

## Strategy Backtests

See the [complete strategy-backtest catalog](strategies/README.md).

## Component Backtests

### [Selection Model](../stages/OPERATIONS.md#selection-and-selection-models)

- [SMA Drawdown Trailing Return Selection Backtest](components/selection-models/sma-drawdown-trailing-return.md)

### [Setup Evaluator](../stages/OPERATIONS.md#setup-evaluators)

- [Setup-Evaluator Forward-Outcome Benchmark](components/setup-evaluators/setup-evaluator-forward-outcome-benchmark.md)

### [Portfolio Policy](../stages/OPERATIONS.md#portfolio-transitions-and-portfolio-policies)

No portfolio-policy component backtests yet.

### [Execution Model](../stages/OPERATIONS.md#execution-and-execution-models)

No execution-model component backtests yet.
