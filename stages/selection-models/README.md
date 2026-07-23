# [Selection Models](../OPERATIONS.md#selection-and-selection-models)

This directory defines reusable ticker selection models.

Descriptors in this directory follow the
[selection-model schema](../DESCRIPTOR-SCHEMA.md#selection-model-schema).

A selection model chooses one or more target tickers from a universe for a
scheduled allocation cycle. It may include eligibility filters, ranking rules,
target weights, and fallback behavior.

## Available Selection Models

- [SMA Drawdown Trailing Return](sma-drawdown-trailing-return.md)
- [Technical Resistance Score](technical-resistance-score.md)
- [Technical Resistance Score SPY SMA200 Gated](technical-resistance-score-spy-sma200-gated.md)
- [Top N SMA Drawdown Trailing Return](top-n-sma-drawdown-trailing-return.md)
