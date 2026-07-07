# TC-001 Full Period

Evaluation window for
[TC-001: High-Beta Universe With SOXL](../../backtests/momentum-rotation/tc-001-high-beta-with-soxl.md).

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
