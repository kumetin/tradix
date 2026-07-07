# Experiments

This directory is reserved for experiment registries and run logs.

Every backtest run that is used for research should eventually be recorded with:

- experiment ID
- timestamp
- strategy
- component profile links
- parameter values
- evaluation partition
- configuration hash
- metrics

The purpose is to preserve the full search history. A good-looking result after
hundreds of tried configurations should be interpreted differently from the same
result after one fixed run.

Generated result data should live under `data/stock/backtests/`. This directory
is for experiment metadata and indexes.
