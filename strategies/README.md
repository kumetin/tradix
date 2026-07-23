# Strategies

This directory contains reusable strategy definitions. A strategy is a
falsifiable thesis about market behavior and predictability, together with the
observable proxies and component constraints required to implement that thesis.
It is not merely a valid pipeline or an arbitrary combination of stages.

Every strategy definition must state:

- the proposed market behavior and mechanism;
- observable point-in-time proxies;
- the predicted outcome and horizon;
- required component behavior;
- thesis-preserving experimental variations;
- substitutions that would create a different thesis; and
- evidence that would falsify or materially weaken the thesis.

Every strategy follows the same canonical decision pipeline. Individual
strategy definitions describe strategy-owned rules, optional operations, and
compatibility requirements; they do not duplicate this table or bind concrete
stage instances or configuration profiles.

## Canonical Strategy Decision Pipeline

| Order | Operation | Responsibility |
| ---: | --- | --- |
| 1 | [Trigger](../stages/OPERATIONS.md#trigger) | Begins a decision cycle and establishes its decision and knowledge cutoffs. |
| 2 | [Universe resolution](../stages/OPERATIONS.md#universe-resolution-and-universe-models) | Produces the point-in-time candidate set from a static configuration or universe model. |
| 3 | [Market-data resolution](../stages/OPERATIONS.md#market-data-resolution) | Supplies only data knowable at the relevant cutoff to the operations that require it. |
| 4 | [Selection](../stages/OPERATIONS.md#selection-and-selection-models) | Applies strategy-specific eligibility and ranking and emits target intent. |
| 5 | Optional [setup evaluation](../stages/OPERATIONS.md#setup-evaluators) | Qualifies selected instruments and may add actionable entry, invalidation, and target levels. Skip this operation when selection already emits sufficient target intent. |
| 6 | [Portfolio transition](../stages/OPERATIONS.md#portfolio-transitions-and-portfolio-policies) | Combines qualified target intent with positions, cash, and constraints to produce order intents. |
| 7 | [Execution](../stages/OPERATIONS.md#execution-and-execution-models) | Applies declared order timing and converts order intents into fills, rejections, costs, settlement movements, and resulting account state. |

[Funding](../stages/OPERATIONS.md#funding-profiles) is an exogenous account event that may occur before or between decision
cycles. [Evaluation](../stages/OPERATIONS.md#evaluation-plans) and benchmarks observe run outputs; they are not downstream
trading stages. Market data and account state are services or inputs even though
their resolution appears in runtime orchestration.

## Run-Mode Bindings

The decision pipeline is shared by historical backtests, paper trading, and
live trading. Each consumer supplies its own surrounding implementations:

| Concern | Backtest | Paper or live trading |
| --- | --- | --- |
| Clock | Historical simulation clock | Wall clock and exchange calendars |
| Market data | Historical point-in-time snapshots | Delayed or live feeds |
| Account state | Simulated positions and cash ledger | Broker account state |
| Execution | Fill, cost, and settlement model | Broker orders and reported fills |
| Funding | Simulated contribution events | Actual account cash movements |
| Evaluation | Historical evaluation plan and benchmarks | Monitoring and post-trade analysis |

Configured strategy backtests belong under `backtests/strategies/`.

## Ownership Boundary

A strategy definition is durable across many configurations and experiments.
It owns the market thesis and the rules that determine whether a variation
preserves or changes that thesis. It does not own runner bindings, evaluation
windows, research status, artifact links, or observed results.

Executable bindings live under
[`backtests/strategies/`](../backtests/strategies/README.md). Research
hypotheses, run registries, findings, and decisions live under
[`experiments/`](../experiments/README.md).

## Available Strategies

- [Classic 12-1 Momentum Rotation](classic-12-1-momentum-rotation.md)
- [Momentum Rotation](momentum-rotation.md)
- [Technical Resistance Runner](technical-resistance-runner.md)
- [Regime-Gated Technical Resistance](regime-gated-technical-resistance.md)
