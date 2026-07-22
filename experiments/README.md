# Experiments

This directory is reserved for experiment registries and run logs.

Every backtest run that is used for research should eventually be recorded with:

- experiment ID
- timestamp
- strategy
- component profile links
- parameter values
- [evaluation](../stages/OPERATIONS.md#evaluation-plans) partition
- configuration hash
- metrics

The purpose is to preserve the full search history. A good-looking result after
hundreds of tried configurations should be interpreted differently from the same
result after one fixed run.

Generated result artifacts should live under `artifacts/stock/backtests/`. This directory
is for experiment metadata and indexes.

## [Setup Evaluator](../stages/OPERATIONS.md#setup-evaluators) Experiments

- [Lower-Risk Swing Entry Baseline: Current Stop](setup-evaluators/lower-risk-swing-entry-baseline-current-stop.md)
- [Lower-Risk Swing Entry Stop-Model Sweep](setup-evaluators/lower-risk-swing-entry-stop-model-sweep.md)
- [Lower-Risk Swing Entry Buy-Limit Sweep](setup-evaluators/lower-risk-swing-entry-buy-limit-sweep.md)
