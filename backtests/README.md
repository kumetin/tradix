# Backtests

This directory contains configured backtest instances. Each backtest selects a
strategy, sets strategy-specific parameters, references reusable platform
profiles, and describes the setup being tested.

Reusable strategy definitions live under `strategies/`. Generic platform
profiles live under directories such as `universes/`, `schedules/`, `funding-profiles/`,
`selection-models/`, `portfolio-policies/`, `execution-models/`, and
`evaluations/`. Generated backtest artifacts should live under
`artifacts/stock/backtests/`.

## Momentum Rotation

- [TC-001: High-Beta Universe With SOXL](momentum-rotation/tc-001-high-beta-with-soxl.md)
- [TC-002: Random Universe](momentum-rotation/tc-002-random-universe.md)
- [TC-003: Random Universe Multi-Position Initial Only](momentum-rotation/tc-003-random-universe-multi-position-initial-only.md)
