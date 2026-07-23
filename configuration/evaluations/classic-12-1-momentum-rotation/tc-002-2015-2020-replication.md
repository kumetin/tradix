# TC-002 2015-2020 Temporal Replication

| Setting | Value |
| --- | --- |
| `warmup_start` | `2014-01-02` |
| `evaluation_start` | `2015-01-02` |
| `evaluation_end` | `2020-12-31` |
| `split_method` | Frozen temporal replication |
| `test_period` | `2015-01-02` to `2020-12-31` |
| `cadence` | Monthly |
| `holdout_status` | Previously unrun full-portfolio configuration; not a clean market-history holdout |

The scenario rules and success criteria are frozen before execution. The
period overlaps earlier component-level analysis and known market history, so
it is robustness evidence rather than a clean holdout. No result-driven rule
change may be retested on this interval.

Warm-up rows initialize the 252-to-21-session signal and are excluded from
reported performance. VFMO is evaluated only from its first locally available
session after its February 2018 inception; it is not represented as cash or
synthetic history before launch.

All fills use the declared
[execution](../../../stages/OPERATIONS.md#execution-and-execution-models)
model and later-session prices.
