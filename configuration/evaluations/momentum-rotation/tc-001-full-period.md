# TC-001 Full Period

[Evaluation](../../../stages/OPERATIONS.md#evaluation-plans) window for
[TC-001: Point-in-Time S&P 500 New-Money Allocation](../../../backtests/strategies/momentum-rotation/tc-001-point-in-time-sp500.md).

| Setting | Value |
| --- | --- |
| `warmup_start` | `2021-01-01` |
| `evaluation_start` | `2021-07-06` |
| `evaluation_end` | `2026-07-02` |
| `split_method` | Single full-period backtest |
| `train_period` | N/A |
| `validation_period` | N/A |
| `test_period` | `2021-07-06` to `2026-07-02` |

This evaluation currently uses one full-period window. Future evaluations can
define rolling or walk-forward train/validation/test splits.
