# Backtests

This directory contains all backtest specifications.

- `strategies/` contains full strategy backtests. Each strategy backtest selects
  a strategy, sets strategy-specific parameters, references reusable platform
  profiles, and describes the setup being tested.
- `components/` contains component-level backtests. Each component backtest
  isolates one reusable component profile under a fixed harness.

Reusable strategy definitions live under `strategies/`. Generic platform
profiles live under directories such as `universes/`, `triggers/`, `funding-profiles/`,
`selection-models/`, `portfolio-policies/`, `execution-models/`, and
`evaluations/`. Generated backtest artifacts should live under
`artifacts/stock/backtests/`.

Run backtests through the root driver:

```sh
python3 scripts/backtests/run_backtest.py BACKTEST_SPEC.md -- DRIVER_ARGS...
```

Driver contracts are documented in
[scripts/backtests/README.md](../scripts/backtests/README.md).

## Strategy Backtests

### Momentum Rotation

- [TC-001: High-Beta Universe With SOXL](strategies/momentum-rotation/tc-001-high-beta-with-soxl.md)
- [TC-002: Random Universe](strategies/momentum-rotation/tc-002-random-universe.md)
- [TC-003: Random Universe Multi-Position Initial Only](strategies/momentum-rotation/tc-003-random-universe-multi-position-initial-only.md)

## Component Backtests

### Trigger

No trigger component backtests yet.

### Universe

No universe component backtests yet.

### Selection Model

- [SMA Drawdown Trailing Return Selection Backtest](components/selection-models/sma-drawdown-trailing-return.md)

### Setup Evaluator

- [Setup Signal Backtest](components/setup-evaluators/setup-signal-backtest.md)

### Portfolio Policy

No portfolio-policy component backtests yet.

### Execution Model

No execution-model component backtests yet.

### Funding Profile

No funding-profile component backtests yet.

### Evaluation Window

No evaluation-window component backtests yet.
