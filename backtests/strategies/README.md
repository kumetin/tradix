# Strategy Backtests

This directory contains executable full-strategy scenarios. Each specification
selects one [strategy thesis](../../strategies/README.md), binds the concrete
[selection model](../../stages/OPERATIONS.md#selection-and-selection-models),
[portfolio policy](../../stages/OPERATIONS.md#portfolio-transitions-and-portfolio-policies),
[execution model](../../stages/OPERATIONS.md#execution-and-execution-models),
and run configuration.

A scenario answers “what exact system can be run?” It may state configuration
intent and a delta from another scenario, but it does not own a research
hypothesis, lifecycle status, success criteria, aggregate findings, or a
decision. Those belong to an [`experiments/`](../../experiments/README.md)
record, which references one or more scenarios without copying their bindings.

Required scenario sections are:

- strategy thesis reference;
- configuration intent;
- universe and optional setup-evaluator binding;
- selection model and genuine strategy parameters;
- [trigger](../../stages/OPERATIONS.md#trigger),
  [funding](../../stages/OPERATIONS.md#funding-profiles), portfolio-policy, and
  execution bindings;
- [evaluation plan](../../stages/OPERATIONS.md#evaluation-plans);
- benchmarks and metrics;
- output location.

## Momentum Rotation

- [TC-001: Point-in-Time S&P 500 New-Money Allocation](momentum-rotation/tc-001-point-in-time-sp500.md) tests concentrated monthly allocation within point-in-time S&P 500 membership.
- [TC-002: Investable US Equities Single-Position Rotation](momentum-rotation/tc-002-investable-us-equities-single-position.md) tests whether the signal survives in a broad investable-US-equities universe.
- [TC-003: Investable US Equities Multi-Position Initial Only](momentum-rotation/tc-003-investable-us-equities-multi-position-initial-only.md) tests the signal with five equal-weight targets and fixed initial capital.

## Regime-Gated Technical Resistance

- [TC-001: Eight-Dataset Robustness](regime-gated-technical-resistance/tc-001-eight-dataset-robustness.md) compares an SPY-SMA200 market gate plus a fixed stop with the ungated, no-stop baseline across five universes and three historical windows.

## Technical Resistance Runner

- [TC-001: Random 50 Universe 1 Monthly Single Position](technical-resistance-runner/tc-001-random-50-universe-1-monthly.md) tests the monthly technical-resistance selector with a sequential two-stage profit-taking policy.
- [TC-002: Random 50 Universe 1 Daily SMA50 Exit](technical-resistance-runner/tc-002-random-50-universe-1-sma50-exit.md) isolates the effect of daily SMA50 invalidation against the otherwise controlled baseline.
- [TC-003: Pre-2014 SMA50 Exit Robustness](technical-resistance-runner/tc-003-pre-2014-sma50-robustness.md) evaluates that frozen SMA50 exit policy in the previously untested 2007–2013 regimes.
