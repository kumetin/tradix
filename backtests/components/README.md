# Component Backtests

This directory contains independent benchmarks for reusable decision or
transformation components.

## Eligibility Rule

A type is eligible to be a reusable component only when it has:

- a stable input/output contract;
- outputs attributable to that component alone; and
- meaningful metrics that compare implementations without running a complete
  strategy.

The stage-side contract and parameters are defined by
[`stages/DESCRIPTOR-SCHEMA.md`](../../stages/DESCRIPTOR-SCHEMA.md). A component
backtest must consume that declared contract rather than inventing a different
test-only interface.

A fixed point-in-time dataset, candidate set, order tape, target-intent tape, or
account-state tape may be supplied as a fixture. Supplying a
[strategy pipeline](../../strategies/README.md#canonical-strategy-decision-pipeline)
as the test harness is not independent benchmarking. If a proposed component
can only be judged by changing it inside a complete strategy, it is not
independently benchmarkable through this layer. Compare it as a strategy-owned
rule or concrete binding under `backtests/strategies/`.

All component backtests are therefore `isolated component backtest` specs. The
former `harnessed component backtest` category is intentionally unsupported.

## Eligible Component Types

| Type | Direct output | Independent comparisons |
| --- | --- | --- |
| [Selection model](../../stages/OPERATIONS.md#selection-and-selection-models) | Eligibility, scores, ranks, targets, and weights | Forward-outcome rank quality, hit rate, monotonicity, stability, and excess return versus same-date candidates |
| [Setup evaluator](../../stages/OPERATIONS.md#setup-evaluators) | Setup classification, score, confidence, and trade-plan levels | Forward return, adverse/favorable excursion, calibration, monotonicity, and reachability |
| [Portfolio policy](../../stages/OPERATIONS.md#portfolio-transitions-and-portfolio-policies) | Orders or transitions from a dated target-intent and account-state tape | Turnover, cash drag, concentration, tracking error, drawdown, and policy constraint adherence |
| [Execution model](../../stages/OPERATIONS.md#execution-and-execution-models) | Fills and cash/settlement ledger from an order and market tape | Fill accuracy, slippage, cost, rejection rate, and settlement correctness |
| Dynamic [universe model](../../stages/OPERATIONS.md#universe-resolution-and-universe-models) | Dated candidate membership from a point-in-time security population | Mandate coverage, investability, membership stability, turnover, and opportunity coverage |

A dynamic universe is eligible only when it has an explicit independently
measurable mandate. A model that ranks securities for expected return is a
selection model even if it is described as universe construction.

## Non-Component Configuration

The following may have reusable configuration profiles, but are not reusable
performance stages:

| Configuration or service | Why it is not a component |
| --- | --- |
| [Trigger](../../stages/OPERATIONS.md#trigger) or schedule | Correct firing can be validated, but opportunity quality is strategy-dependent. |
| Static universe | A ticker list is input data, not behavior. |
| [Funding profile](../../stages/OPERATIONS.md#funding-profiles) | Contributions are exogenous run inputs. |
| [Evaluation plan](../../stages/OPERATIONS.md#evaluation-plans) | Windows, splits, warm-up, and holdouts define the test. |
| Market-data provider | Data quality, latency, and completeness are operational validation concerns. |
| Benchmark set | Benchmarks define comparison context. |

## Required Sections

| Section | Purpose |
| --- | --- |
| Component binding | Use `Component Under Test` for a descriptor-specific spec or `Applicable Component Type` for a generic protocol. |
| Question | State the component behavior being measured. |
| Backtest Type | Declare `isolated component backtest`. |
| Direct Input/Output Contract | Define the fixture inputs and attributable outputs. |
| Variants | List parameter values or competing implementations. |
| Evaluation Requirements | State required partition, warm-up, regime, and holdout properties; the experiment binds the concrete evaluation plan. |
| Metrics | Define contract-level comparison metrics. |
| Baselines | Declare simple output-level baselines or competing implementations. |
| Interpretation Rules | Define evidence for reuse, rejection, or conditional use. |
| Output Location | Point to `artifacts/stock/backtests/components/`. |

## Relationship to Experiments

A component backtest is a reusable measurement protocol, not a run registry.
It may either target one named stage descriptor or accept any implementation
of a declared component type. State which form it uses:

- Use `Component Under Test` when the spec is intentionally tied to one stage
  descriptor.
- Use `Applicable Component Type` when experiments supply the concrete
  stage descriptor.

Concrete research grids, lifecycle status, artifact run links, aggregate
results, and decisions belong in [`experiments/`](../../experiments/README.md).
An experiment binds a stage descriptor to this spec and an
[evaluation plan](../../stages/OPERATIONS.md#evaluation-plans). Do not add
completed-run references to the reusable backtest spec.

Generated artifacts belong under:

```text
artifacts/stock/backtests/components/<component-type>/<backtest-id>/
```
