# Strategies

This directory contains reusable strategy definitions: the rules, data
requirements, portfolio behavior, and parameters that define how a strategy
works.

Strategy flow files define the canonical ordered pipeline for a strategy.
Backtests, paper-trading runners, and future live bots should consume the same
strategy flow and supply run-mode-specific configuration around it.

Configured strategy backtests belong under `backtests/strategies/`.

## Available Strategies

- [Momentum Rotation](momentum-rotation.md)
- [Momentum Rotation Flow](momentum-rotation.flow.md)
