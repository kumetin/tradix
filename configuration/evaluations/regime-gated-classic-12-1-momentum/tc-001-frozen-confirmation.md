# TC-001 Frozen Confirmation

| Setting | Value |
| --- | --- |
| `warmup_start` | `2020-01-02` |
| `evaluation_start` | `2021-01-04` |
| `evaluation_end` | `2026-07-02` |
| `split_method` | One-shot strategy-specific comparison against frozen ungated run |
| `development_evidence` | Classic 12-1 validation and general SMA200 risk-control thesis |
| `test_period` | `2021-01-04` to `2026-07-02` |
| `cadence` | Monthly |
| `holdout_status` | Frozen before gated execution, but not a clean market-history holdout |

The exact gated configuration and success criteria were written before its
results were inspected. The period is not called a clean holdout because the
ungated strategy and broad market history were already inspected. It is a
one-shot strategy-specific confirmation; no gate, target-count, signal, or
timing or [execution](../../../stages/OPERATIONS.md#execution-and-execution-models)
change may be made from its outcome and retested on this window.

Warm-up observations initialize signals and SMA200 and are excluded from
reported performance.
