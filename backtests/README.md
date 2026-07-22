# Backtests

This directory contains all backtest specifications.

- `strategies/` contains full strategy backtests. Each strategy backtest selects
  a falsifiable strategy thesis, binds reusable platform profiles and parameter
  values, and states the thesis claim or robustness dimension being tested.
- `components/` contains independent component benchmarks. A component must
  expose a direct contract that can be compared without a complete strategy.

[Reusable strategy definitions](../strategies/README.md) live under
`strategies/`. Independently
benchmarkable components and their descriptors live together under `stages/`.
Static
universes, [triggers](../stages/OPERATIONS.md#trigger), [funding profiles](../stages/OPERATIONS.md#funding-profiles), and evaluations are configuration inputs,
not performance components. Generated backtest artifacts should live under
`artifacts/stock/backtests/`.

Run backtests through the root driver:

```sh
python3 scripts/backtests/run_backtest.py BACKTEST_SPEC.md -- DRIVER_ARGS...
```

Driver contracts are documented in
[scripts/backtests/README.md](../scripts/backtests/README.md).

## Strategy Backtests

### Momentum Rotation

- [TC-001: Point-in-Time S&P 500 New-Money Allocation](strategies/momentum-rotation/tc-001-point-in-time-sp500.md)
- [TC-002: Investable US Equities Single-Position Rotation](strategies/momentum-rotation/tc-002-investable-us-equities-single-position.md)
- [TC-003: Investable US Equities Multi-Position Initial Only](strategies/momentum-rotation/tc-003-investable-us-equities-multi-position-initial-only.md)

## Component Backtests

### [Selection Model](../stages/OPERATIONS.md#selection-and-selection-models)

- [SMA Drawdown Trailing Return Selection Backtest](components/selection-models/sma-drawdown-trailing-return.md)

### [Setup Evaluator](../stages/OPERATIONS.md#setup-evaluators)

- [Setup Signal Backtest](components/setup-evaluators/setup-signal-backtest.md)

### [Portfolio Policy](../stages/OPERATIONS.md#portfolio-transitions-and-portfolio-policies)

No portfolio-policy component backtests yet.

### [Execution Model](../stages/OPERATIONS.md#execution-and-execution-models)

No execution-model component backtests yet.
