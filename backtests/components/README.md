# Component Backtests

This directory contains component-level backtest specifications for reusable
platform component profiles.

A component backtest is not a full strategy thesis. It evaluates one component
profile, or a small parameter family of that profile, with the smallest
simulation surface that still preserves the behavior being measured. The goal
is to build reusable evidence before composing a complete strategy backtest.

## Terminology

| Term | Meaning |
| --- | --- |
| Component type | The role in the platform, such as [selection model](../../selection-models/README.md), [setup evaluator](../../setup-evaluators/README.md), [portfolio policy](../../portfolio-policies/README.md), [execution model](../../execution-models/README.md), [universe](../../universes/README.md), [trigger](../../triggers/README.md), [funding profile](../../funding-profiles/README.md), or [evaluation window](../../evaluations/README.md). |
| Component profile | A concrete reusable implementation of a component type, such as `selection-models/sma-drawdown-trailing-return.md`. |
| Component backtest | A repeatable historical test of one component profile. |
| Isolated component backtest | Tests a component's own outputs directly against historical outcomes with no larger strategy dependency. |
| Harnessed component backtest | Tests one component inside a fixed strategy harness while holding surrounding stages constant. |
| Benchmark | The baseline or comparison target, such as `SPY`, equal-weight universe exposure, random scoring, or an older component profile. |
| Benchmark harness | The fixed surrounding configuration used to isolate the component being tested. |

## Backtest Types

### Isolated Component Backtest

Use an isolated component backtest when the component emits a measurable signal,
decision, transformation, or event that can be compared directly with
historical outcomes.

Examples:

- A [setup evaluator](../../setup-evaluators/README.md) emits `buy`, `wait`, or `avoid` signals with score,
  confidence, stop loss, and take profit levels.
- A [trigger](../../triggers/README.md) profile is tested for signal freshness, missed opportunities, or
  excessive firing frequency.
- An [execution model](../../execution-models/README.md) is tested against synthetic orders and historical price
  bars.

### Harnessed Component Backtest

Use a harnessed component backtest when the component's effect only has meaning
after interacting with other strategy stages. The harness should be fixed,
minimal, and explicit.

Examples:

- A [selection model](../../selection-models/README.md) is plugged into a monthly allocation strategy while the
  [trigger](../../triggers/README.md), [universe](../../universes/README.md),
  [portfolio policy](../../portfolio-policies/README.md),
  [execution model](../../execution-models/README.md), [funding profile](../../funding-profiles/README.md), and
  evaluation window stay fixed.
- A [portfolio policy](../../portfolio-policies/README.md) is tested while the
  [selection model](../../selection-models/README.md), [trigger](../../triggers/README.md),
  [execution model](../../execution-models/README.md), [funding profile](../../funding-profiles/README.md), and
  [universe](../../universes/README.md) stay fixed.

Rule of thumb: use isolated when the component output can be measured directly;
use harnessed when the component must interact with portfolio, account, or
strategy state before its behavior is meaningful.

## When To Use This Layer

Use a component backtest when the question is narrow:

- Does this [selection model](../../selection-models/README.md) rank better than the baseline selector across
  multiple periods?
- Does this [setup evaluator](../../setup-evaluators/README.md) emit signals that produce durable realized returns?
- Does this [portfolio policy](../../portfolio-policies/README.md) reduce drawdown or turnover without excessive
  cash drag?
- Does this [execution model](../../execution-models/README.md) materially change results because of settlement,
  slippage, fees, or fractional-share assumptions?
- Is a parameter family stable enough to reuse, or only fitted to one period?

Use `backtests/strategies/` when the question is whether a complete strategy
configuration works end to end.

## Required Sections

Each component backtest spec should include:

| Section | Purpose |
| --- | --- |
| Component Under Test | Link the component profile and name its component type. |
| Question | State the narrow behavior or edge being measured. |
| Backtest Type | Declare `isolated component backtest` or `harnessed component backtest`. |
| Fixed Harness | For harnessed tests, link every surrounding strategy, trigger, universe, portfolio policy, execution model, funding profile, and evaluation profile held constant. For isolated tests, state `N/A` and define the direct input/output contract. |
| Variants | List parameter values or competing profiles being compared. |
| Evaluation Matrix | List evaluation windows, market regimes, or train/validation/test splits. |
| Metrics | Define the metrics used to compare variants. |
| Baselines | Declare simple comparisons such as `SPY`, equal-weight universe, previous profile, or random selector. |
| Interpretation Rules | Explain what result would make the component reusable, rejected, or only conditionally useful. |
| Output Location | Point generated artifacts under `artifacts/stock/backtests/components/`. |

## Output Layout

Generated component backtest artifacts should live under:

```text
artifacts/stock/backtests/components/<component-type>/<backtest-id>/
```

Do not store generated result CSVs, charts, or logs in this directory.
