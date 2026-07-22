# Universes

This directory contains static ticker-set configuration used by strategies,
backtests, and evaluations. A [static universe](../../stages/OPERATIONS.md#universe-resolution-and-universe-models) is not a reusable performance
stage because it has no behavior or independently attributable output.

A dynamic universe implementation may qualify as a component only when it maps
a point-in-time security population to dated membership under an explicit,
independently benchmarkable mandate. Return-ranking logic belongs to a
[selection model](../../stages/OPERATIONS.md#selection-and-selection-models) even when used upstream to narrow candidates.

Dynamic universe models follow the
[`Universe Model Schema`](../../stages/DESCRIPTOR-SCHEMA.md#universe-model-schema)
and live under `stages/universe-models/`; this directory remains the home of
static ticker-set configuration. Valid dynamic mandates include point-in-time
external membership, explicitly defined market coverage, and fixed
investability constraints. Every descriptive term must reduce to concrete
effective-dated fields, predicates, ordering, and deterministic tie-breakers.

Static universe definitions only supply candidate instruments. Fallback
selection belongs to the configured selection model.

## Available Static Universes

None. The former curated high-beta and random-20 fixtures were removed in favor
of query-defined universe models under `stages/universe-models/`.
