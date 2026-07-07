# TC-002 Full Period

Evaluation window for
[TC-002: Random Universe](../../backtests/momentum-rotation/tc-002-random-universe.md).

| Setting | Value |
| --- | --- |
| `warmup_start` | `2021-01-01` |
| `evaluation_start` | `2021-07-06` |
| `evaluation_end` | `2026-07-02` |
| `split_method` | Single full-period backtest |
| `train_period` | N/A |
| `validation_period` | N/A |
| `test_period` | `2021-07-06` to `2026-07-02` |

This evaluation currently uses the same full-period window as TC-001 so the
random-universe setup can be compared directly against the curated high-beta
setup.
