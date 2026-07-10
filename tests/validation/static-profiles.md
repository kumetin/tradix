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
| Fallback ticker is present | `fallback_ticker` must be in the universe ticker list. |
| Duplicate tickers | No duplicate ticker entries. |
| Local data availability | Required tickers exist in the local price dataset for the evaluation window or are explicitly marked unavailable. |

## Funding

| Check | Expected |
| --- | --- |
| Initial capital | Non-negative. |
| Recurring contribution | Non-negative. |
| Initial-only profile | Monthly contribution is `$0`. |

## Schedules

| Check | Expected |
| --- | --- |
| Rebalance frequency | Recognized value such as monthly, weekly, quarterly, or explicit dates. |
| Signal cutoff | Schedule defines when signal data is allowed to be known. |

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
| Referenced files exist | Strategy, universe, selection model, schedule, funding, portfolio policy, execution model, and evaluation links resolve. |
| Compatible selection/policy | Single-position policies receive one target; multi-position policies receive weighted targets. |
| Compatible execution/policy | Policies that depend on settled cash use an execution model that defines settlement behavior. |
| Benchmarks declared | Results should be compared to `SPY` and, when possible, an equal-weight universe benchmark. |

## Component Benchmarks

| Check | Expected |
| --- | --- |
| Referenced files exist | Component under test, fixed harness profiles, evaluation profiles, and baseline links resolve. |
| Component under test declared | The spec names one component type and links one primary component profile. |
| Fixed harness declared | The surrounding strategy, schedule, universe, portfolio policy, execution model, and funding profile are explicit. |
| Evaluation and metrics declared | Evaluation matrix and metrics sections are present. |
| Output location declared | Generated outputs are written under `data/stock/component-benchmarks/`. |
