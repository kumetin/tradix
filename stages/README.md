# Reusable Stages

This directory is the single registry for independently benchmarkable stages.
Each stage type keeps its reusable descriptors and, when present, its executable
implementation together.

All stage families and concrete descriptors must follow the
[Reusable Stage Descriptor Schema](DESCRIPTOR-SCHEMA.md). That document defines
the common descriptor fields, parameter-table format, stage-instance reference,
and type-specific input/configuration/output contracts.

The canonical responsibility and benchmarking guide for pipeline operations,
stage types, and run configuration is
[Strategy Operations and Stage Responsibilities](OPERATIONS.md).

## Eligibility

A stage belongs here only when it exposes a stable input/output contract and can
be compared with a baseline or another implementation without running a
complete strategy.

| Stage type | Descriptor and implementation directory |
| --- | --- |
| [Universe model](OPERATIONS.md#universe-resolution-and-universe-models) | [`universe-models/`](universe-models/README.md) |
| [Selection model](OPERATIONS.md#selection-and-selection-models) | [`selection-models/`](selection-models/README.md) |
| [Setup evaluator](OPERATIONS.md#setup-evaluators) | [`setup-evaluators/`](setup-evaluators/README.md) |
| [Portfolio policy](OPERATIONS.md#portfolio-transitions-and-portfolio-policies) | [`portfolio-policies/`](portfolio-policies/README.md) |
| [Execution model](OPERATIONS.md#execution-and-execution-models) | [`execution-models/`](execution-models/README.md) |

[Triggers](OPERATIONS.md#trigger), static universes,
[funding profiles](OPERATIONS.md#funding-profiles), and
[evaluation plans](OPERATIONS.md#evaluation-plans) live under
[`configuration/`](../configuration/README.md). Benchmarks and market-data
providers are services or infrastructure. These types configure or support a
strategy run but are not independently benchmarkable performance stages.

Stage benchmarks remain under `backtests/components/`, behavioral contract tests
under `tests/`, and generated results under `artifacts/stock/backtests/components/`.
