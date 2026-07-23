# Experiments

This directory is the research registry. One file represents one falsifiable
research question from proposal through decision. It may index many immutable
backtest runs.

## Ownership Boundaries

| Location | Owns | Must not own |
| --- | --- | --- |
| `backtests/components/` | Reusable component measurement protocol: input/output contract, outcome model, metrics, baselines, interpretation rules, and artifact schema | Concrete research grids, experiment status, conclusions, or run history |
| `backtests/strategies/` | Executable full-strategy scenarios: strategy reference, concrete component/configuration bindings, resolved strategy parameters, accounting, metrics, benchmarks, and output contract | A second market thesis, experiment lifecycle state, success criteria, conclusions, or run history |
| `configuration/evaluations/` | Reusable [evaluation](../stages/OPERATIONS.md#evaluation-plans) windows, partitions, warm-up rules, and holdout policy | Experiment grids, results, or promotion decisions |
| `strategies/` | Durable market thesis, mechanism, point-in-time proxies, prediction horizon, required behavior, thesis boundaries, and falsification criteria | Concrete runner bindings, evaluation windows, experiment status, or results |
| `experiments/` | Research hypothesis, reference configuration, declared deltas, success criteria, lifecycle status, run index, findings, and decision | A duplicated strategy thesis, copied full backtest configuration, or generated CSV/HTML output |
| `artifacts/stock/backtests/` | Immutable output for one exact run, including its resolved configuration | Cross-run research conclusions or mutable experiment status |

Strategy research references flow in one direction:

```text
experiment
  -> strategy backtest scenario
       -> strategy thesis
       -> stage descriptors and configuration profiles
       -> evaluation plan
  -> artifact runs
```

Component research uses a narrower chain because a generic component protocol
does not contain a configured full-strategy scenario:

```text
experiment
  -> stage descriptor
  -> component backtest protocol
  -> evaluation plan
  -> artifact runs
```

Upstream definitions do not link back to completed experiments. Catalog links
are allowed, but status, results, and decisions flow only downstream.

## Required Experiment Sections

Use the following order for new experiment files:

| Section | Purpose |
| --- | --- |
| Experiment ID | Stable, unique identifier matching the filename. |
| Status | Current lifecycle state. |
| Question or Hypothesis | Falsifiable claim being tested. |
| Reference Configuration | For strategy research, link one strategy scenario. For component research, link the stage descriptor, component-backtest protocol, and evaluation plan. |
| Declared Deltas | Only values varied or overridden relative to the reference configuration. Use `None` for a fixed baseline experiment. |
| Success Criteria | Criteria fixed before inspecting the relevant results. |
| Run Index | Links to every artifact run, including failed or losing runs. |
| Results | Cross-run summary; use `Pending` before execution. |
| Findings | Interpretation of the results. |
| Decision | Promotion, rejection, or follow-up decision. |
| Follow-up | Next experiment or required work, when applicable. |

Valid statuses are:

```text
draft
ready
running
completed
rejected_for_promotion
promoted
abandoned
```

`Status` describes the experiment record, not an individual artifact run.
Operational [execution](../stages/OPERATIONS.md#execution-and-execution-models)
success or failure of a run belongs in that run's
`execution-report.md`.

Every research run should be listed in its experiment's Run Index with the run
timestamp/scenario, evaluation partition, configuration hash (normally encoded
in the artifact directory), and artifact link. Exact resolved parameter values
remain in the artifact's `run_config.csv`; the experiment summarizes only the
dimensions needed to compare runs.

### Strategy Experiment Rule

A strategy experiment must not repeat the backtest scenario's universe,
stage descriptors, [funding](../stages/OPERATIONS.md#funding-profiles),
[portfolio policy](../stages/OPERATIONS.md#portfolio-transitions-and-portfolio-policies),
execution, accounting, evaluation window, metrics, or benchmarks. It references the scenario and
records only declared deltas. If a setting is intended to be reused as a
standalone executable configuration, create another strategy-backtest scenario
and compare the two scenario links from the experiment.

### Component Experiment Rule

A component experiment is itself the configured research layer above a generic
component protocol. It therefore selects the concrete stage descriptor,
evaluation plan/partition, fixture, and parameter grid. It should reference
evaluation dates and defaults by name rather than copying them; exact resolved
values remain in each artifact's `run_config.csv`.

Generated result artifacts live under `artifacts/stock/backtests/`. This
directory contains experiment metadata and indexes, never copied result files.

## [Setup Evaluator](../stages/OPERATIONS.md#setup-evaluators) Experiments

- [Lower-Risk Swing Entry Baseline: Current Stop](setup-evaluators/lower-risk-swing-entry-baseline-current-stop.md)
- [Lower-Risk Swing Entry Stop-Model Sweep](setup-evaluators/lower-risk-swing-entry-stop-model-sweep.md)
- [Lower-Risk Swing Entry Buy-Limit Sweep](setup-evaluators/lower-risk-swing-entry-buy-limit-sweep.md)
