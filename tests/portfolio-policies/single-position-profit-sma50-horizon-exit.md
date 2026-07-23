# Component Test: Single Position Profit SMA50 Horizon Exit

Component: [Single Position Profit SMA50 Horizon Exit](../../stages/portfolio-policies/single-position-profit-sma50-horizon-exit.md)

## Purpose

Verify daily [portfolio-policy](../../stages/OPERATIONS.md#portfolio-transitions-and-portfolio-policies)
invalidation independently from the monthly entry
[trigger](../../stages/OPERATIONS.md#trigger) and its
[execution](../../stages/OPERATIONS.md#execution-and-execution-models).

## Expected Behavior

| Case | Given after the completed session | Expected order intent |
| --- | --- | --- |
| Below SMA50 | Close `99.99`, same-day SMA50 `100.00` | Full liquidation at next valid session open. |
| Equal to SMA50 | Close `100.00`, SMA50 `100.00` | No SMA50 order. |
| Above SMA50 | Close `100.01`, SMA50 `100.00` | No SMA50 order. |
| Entry day below | Entry filled at open; completed entry-day close below SMA50 | Next-session-open liquidation. |
| Same-session execution | Below signal is first known after close | Never fill at that close. |
| Pending signal | Prior session signaled; new session also touches profit target | Next-open SMA50 liquidation has priority. |
| Missing SMA50 | Close exists but SMA50 is missing | Retain, report constraint event, do not infer or forward-fill. |
| Horizon | No earlier exit through session 126 | Liquidate at session-126 close. |

## Metrics

| Metric | Pass condition |
| --- | --- |
| `false_signal_count` | `0` for equal, above, or missing inputs. |
| `same_close_fill_count` | `0`. |
| `next_open_delay_sessions` | `1` valid session after every accepted signal. |
| `entry_day_coverage` | Entry-day completed row is tested. |
| `deterministic_replay` | Identical input tape emits identical order intents. |

Executable helper coverage lives in `tests/test_sma50_exit_policy.py`.
