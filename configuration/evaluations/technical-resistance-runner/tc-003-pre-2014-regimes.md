# Technical Resistance Runner TC-003 Pre-2014 Regimes

[Evaluation](../../../stages/OPERATIONS.md#evaluation-plans) plan for frozen
pre-2014 robustness windows not used in the original 2015–2026 experiments.

| Setting | Value |
| --- | --- |
| `warmup_start` | `2004-01-02` |
| `evaluation_start` | `2007-01-03` |
| `evaluation_end` | `2013-12-31` |
| `split_method` | Two fixed, non-overlapping historical regime windows |
| `financial_crisis_window` | `2007-01-03` to `2009-12-31` |
| `recovery_expansion_window` | `2010-01-04` to `2013-12-31` |
| `holdout_status` | Previously unrun dates, but current-constituent biased |

Rows before `evaluation_start` are warm-up only and must not enter reported
performance metrics. Report both windows separately; do not pool them into a
single headline result.

The strategy and SMA50 policy were frozen before these windows were run.
However, current universe membership is projected backward and creates severe
survivorship/current-constituent bias. These windows are new temporal evidence,
not a clean point-in-time S&P 500 holdout.
