# Component Benchmarks

This directory contains isolated benchmark specifications for reusable platform
component profiles.

A component benchmark is not a full strategy thesis. It evaluates one component
profile, or a small parameter family of that profile, while holding the rest of
the harness fixed. The goal is to build reusable evidence before composing a
complete strategy backtest.

## Terminology

| Term | Meaning |
| --- | --- |
| Component type | The role in the platform, such as selection model, portfolio policy, execution model, universe, schedule, funding profile, or evaluation window. |
| Component profile | A concrete reusable implementation of a component type, such as `selection-models/sma-drawdown-trailing-return.md`. |
| Strategy stage | A component type viewed in the ordered strategy flow. Prefer this term only when discussing sequencing. |
| Benchmark harness | The fixed surrounding configuration used to isolate the component being tested. |
| Component benchmark | A repeatable evaluation of one component profile under a benchmark harness. |

Prefer `component type` over `archetype`; it is shorter and clearer. Prefer
`component profile` over `instance` for reusable markdown definitions, because
`instance` is already useful for a configured backtest run.

## When To Use This Layer

Use a component benchmark when the question is narrow:

- Does this selection model rank better than the baseline selector across
  multiple periods?
- Does this portfolio policy reduce drawdown or turnover without excessive
  cash drag?
- Does this execution model materially change results because of settlement,
  slippage, fees, or fractional-share assumptions?
- Is a parameter family stable enough to reuse, or only fitted to one period?

Use `backtests/` when the question is whether a complete strategy configuration
works end to end.

## Required Sections

Each benchmark spec should include:

| Section | Purpose |
| --- | --- |
| Component Under Test | Link the component profile and name its component type. |
| Question | State the narrow behavior or edge being measured. |
| Fixed Harness | Link every surrounding strategy, schedule, universe, portfolio policy, execution model, funding profile, and evaluation profile held constant. |
| Variants | List parameter values or competing profiles being compared. |
| Evaluation Matrix | List evaluation windows, market regimes, or train/validation/test splits. |
| Metrics | Define the metrics used to compare variants. |
| Baselines | Declare simple comparisons such as `SPY`, equal-weight universe, previous profile, or random selector. |
| Interpretation Rules | Explain what result would make the component reusable, rejected, or only conditionally useful. |
| Output Location | Point generated outputs under `data/stock/component-benchmarks/`. |

## Suggested Metrics By Component Type

Selection model benchmarks should track return, drawdown, volatility,
selection turnover, fallback rate, concentration, hit rate versus equal-weight
universe, and benchmark-relative return.

Portfolio policy benchmarks should track total return, max drawdown, turnover,
realized churn, average cash drag, missed exposure, tax or fee sensitivity when
modeled, and contribution deployment speed.

Execution model benchmarks should track fill drag, fee drag, slippage drag,
settlement delays, rejected or deferred orders, fractional-share impact, and
cash reuse assumptions.

Universe benchmarks should track survivorship or current-universe bias,
coverage gaps, ticker availability through time, benchmark-relative return,
concentration, and fallback usage.

Schedule benchmarks should track signal freshness, turnover, missed moves,
monthly or weekly seasonality sensitivity, and benchmark-relative return.

Funding benchmarks should track capital deployment timing, contribution timing
sensitivity, and whether a component's apparent edge depends on unrealistic
cash arrival assumptions.

Evaluation benchmarks should track train/validation/test stability, holdout
degradation, walk-forward consistency, and warm-up exclusion behavior.

## Output Layout

Generated benchmark outputs should live under:

```text
data/stock/component-benchmarks/<component-type>/<benchmark-id>/
```

Do not store generated result CSVs, charts, or logs in this directory.
