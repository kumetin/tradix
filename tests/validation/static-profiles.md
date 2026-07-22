# Validation: Static Profiles

Static profile validation checks configuration consistency for component files
that mostly contain data rather than behavior.

Executable check:

```sh
python3 tests/validation/validate_static_profiles.py
```

## Universes

| Check | Expected |
| --- | --- |
| Universe has tickers | At least one ticker is listed. |
| Optional legacy fallback is valid | When present, it must be in the ticker list; new fallbacks belong to [selection](../../stages/OPERATIONS.md#selection-and-selection-models)-model instances. |
| Duplicate tickers | No duplicate ticker entries. |
| Local data availability | Required tickers exist in the local price dataset for the [evaluation](../../stages/OPERATIONS.md#evaluation-plans) window or are explicitly marked unavailable. |

## [Funding](../../stages/OPERATIONS.md#funding-profiles)

| Check | Expected |
| --- | --- |
| Initial capital | Non-negative. |
| Recurring contribution | Non-negative. |
| Initial-only profile | Monthly contribution is `$0`. |

## [Triggers](../../stages/OPERATIONS.md#trigger)

| Check | Expected |
| --- | --- |
| Trigger frequency | Recognized value such as monthly, weekly, quarterly, or explicit dates. |
| Signal cutoff | Trigger defines when signal data is allowed to be known. |

## [Strategy Pipeline](../../strategies/README.md#canonical-strategy-decision-pipeline)

The canonical, run-mode-independent operation order is documented once in
[the strategy concepts guide](../../strategies/README.md). Individual strategy
files describe only strategy-owned rules and pipeline placement; backtests bind
concrete profiles.

## Evaluations

| Check | Expected |
| --- | --- |
| Date order | `warmup_start <= evaluation_start <= evaluation_end`. |
| Split order | Train, validation, and test periods do not overlap unless explicitly intended. |
| Leakage guard | Evaluation defines what data is available at each simulated decision point. |
| Warm-up exclusion | Warm-up-only rows are excluded from reported performance metrics. |
| Holdout labeling | Locked holdout periods are explicitly labeled when used. |

## Backtests

| Check | Expected |
| --- | --- |
| Referenced files exist | Strategy, universe, selection model, trigger, funding, [portfolio policy](../../stages/OPERATIONS.md#portfolio-transitions-and-portfolio-policies), [execution model](../../stages/OPERATIONS.md#execution-and-execution-models), and evaluation links resolve. |
| Compatible selection/policy | Single-position policies receive one target; multi-position policies receive weighted targets. |
| Compatible execution/policy | Policies that depend on settled cash use an execution model that defines settlement behavior. |
| Benchmarks declared | Results should be compared to `SPY` and, when possible, an equal-weight universe benchmark. |

## Component Backtests

| Check | Expected |
| --- | --- |
| Referenced files exist | Component under test, evaluation profiles, and baseline links resolve. |
| Component under test declared | The spec names one component type and links one primary component profile. |
| Direct contract declared | Fixture inputs and outputs attributable to the component are explicit. |
| Evaluation and metrics declared | Evaluation matrix and metrics sections are present. |
| Output location declared | Generated artifacts are written under `artifacts/stock/backtests/components/`. |
