# Technical Resistance Runner TC-001 Development and Retrospective Period

[Evaluation](../../../stages/OPERATIONS.md#evaluation-plans) plan for
[TC-001: Random 50 Universe 1 Monthly Single Position](../../../backtests/strategies/technical-resistance-runner/tc-001-random-50-universe-1-monthly.md).

| Setting | Value |
| --- | --- |
| `warmup_start` | `2014-01-02` |
| `evaluation_start` | `2015-01-02` |
| `evaluation_end` | `2026-07-17` |
| `split_method` | Development period plus contaminated retrospective period |
| `development_period` | `2015-01-02` to `2024-12-31` |
| `validation_period` | Walk-forward folds inside development period |
| `retrospective_period` | `2025-01-02` to `2026-07-17` |
| `test_period` | None; a new untouched period is required |
| `holdout_status` | Contaminated by rule changes made after observing results |

Rows before `evaluation_start` are warm-up only and must not enter reported
performance metrics. Each walk-forward fold may train or calibrate diagnostics
only on earlier development rows and must evaluate on the immediately following
non-overlapping fold.

The `2025-01-02` to `2026-07-17` interval was originally inspected as a locked
holdout. The exit rule was subsequently changed after its result was known, so
that interval is now retrospective development evidence and must not be
described as out of sample. A new untouched future or independently reserved
period is required for a clean test.

Report development, walk-forward validation, and the contaminated retrospective
period separately. Do not pool them into a single headline statistic without
also showing each partition and its status.
