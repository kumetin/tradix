# [Universe Models](../OPERATIONS.md#universe-resolution-and-universe-models)

This directory defines reusable dynamic universe models.

Descriptors in this directory follow the
[`universe-model` schema](../DESCRIPTOR-SCHEMA.md#universe-model-schema).

A universe model maps a point-in-time security population to a dated candidate
set under an explicit coverage or investability mandate. Its rules must reduce
to concrete effective-dated fields, predicates, ordering, limits, missing-data
behavior, and deterministic tie-breakers.

Universe models do not estimate investment attractiveness or emit portfolio
targets. Strategy-specific eligibility, expected-return signals, ranking for
ownership, target count, target weights, and fallback [selection](../OPERATIONS.md#selection-and-selection-models) belong to a
selection model.

Static ticker lists remain configuration under
[`configuration/universes/`](../../configuration/universes/).

## Available Universe Models

- [Point-in-Time S&P 500](point-in-time-sp500.md)
- [Investable US Equities Top 1000](investable-us-equities-top-1000.md)
