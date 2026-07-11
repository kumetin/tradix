# TC-003 Full Period

Evaluation window for
[TC-003: Random Universe Multi-Position Initial Only](../../backtests/strategies/momentum-rotation/tc-003-random-universe-multi-position-initial-only.md).

| Setting | Value |
| --- | --- |
| `warmup_start` | `2021-01-01` |
| `evaluation_start` | `2021-07-06` |
| `evaluation_end` | `2026-07-02` |
| `split_method` | Single full-period backtest |
| `train_period` | N/A |
| `validation_period` | N/A |
| `test_period` | `2021-07-06` to `2026-07-02` |

This evaluation uses the same full-period window as TC-001 and TC-002 so the
multi-position initial-only setup can be compared against the accumulation and
single-position variants.
