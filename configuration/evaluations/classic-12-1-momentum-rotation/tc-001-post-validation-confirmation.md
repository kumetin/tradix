# TC-001 Post-Validation Confirmation

[Evaluation](../../../stages/OPERATIONS.md#evaluation-plans) plan for
[TC-001: Point-in-Time S&P 500 Top-10 Monthly Rotation](../../../backtests/strategies/classic-12-1-momentum-rotation/tc-001-point-in-time-sp500-top-10.md).

| Setting | Value |
| --- | --- |
| `warmup_start` | `2020-01-02` |
| `evaluation_start` | `2021-01-04` |
| `evaluation_end` | `2026-07-02` |
| `split_method` | Chronological post-validation confirmation; not a locked holdout |
| `train_period` | N/A; signal and portfolio parameters are frozen |
| `validation_period` | `2016-01-04` to `2020-12-31`, consumed by component validation |
| `test_period` | `2021-01-04` to `2026-07-02` |
| `cadence` | Monthly |

Warm-up rows initialize the 252-to-21-session signal and are excluded from all
reported portfolio-performance metrics.

The test period begins after the component-validation window, but it is not
called a locked holdout because its broad market history was already knowable
when this plan was written. The selector, target count, weighting,
[trigger](../../../stages/OPERATIONS.md#trigger),
[portfolio policy](../../../stages/OPERATIONS.md#portfolio-transitions-and-portfolio-policies),
and
[execution](../../../stages/OPERATIONS.md#execution-and-execution-models)
bindings must remain frozen throughout this confirmation run. Any changes
prompted by these results require a new scenario and a later untouched period
or different point-in-time market.

Report results for the full window and separately for each calendar year.
Coverage and missing departed-security outcomes must accompany performance
metrics; incomplete coverage cannot be hidden by calculating results only from
surviving names.
