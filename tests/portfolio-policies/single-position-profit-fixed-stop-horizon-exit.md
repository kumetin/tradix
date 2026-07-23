# Component Test: Single Position Profit Fixed Stop Horizon Exit

Component: [Single Position Profit Fixed Stop Horizon Exit](../../stages/portfolio-policies/single-position-profit-fixed-stop-horizon-exit.md)

## Purpose

Verify protective-stop
[portfolio-policy](../../stages/OPERATIONS.md#portfolio-transitions-and-portfolio-policies)
behavior and conservative
[execution](../../stages/OPERATIONS.md#execution-and-execution-models).

## Expected Behavior

| Case | Given | Expected |
| --- | --- | --- |
| Untouched | Low remains above stop | No stop fill. |
| Intraday touch | Open above stop; low at/below stop | Fill at stop. |
| Gap through | Open and low below stop | Fill at worse open. |
| Ambiguous target/stop bar | Both levels touched with unknown path | Stop has priority. |
| Missing bar | Required open or low absent | Retain and report; do not infer. |
| Horizon | No earlier exit by session 126 | Liquidate at close. |

## Metrics

- deterministic fill price;
- zero inferred missing-bar fills;
- stop-first ambiguous-bar count;
- gap-through loss; and
- cash conservation after costs.

Executable helper coverage lives in `tests/test_fixed_stop_policy.py`.
