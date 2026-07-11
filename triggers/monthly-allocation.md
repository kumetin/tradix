# Monthly Allocation

Generates one allocation opportunity at the start of each month.

Signals and rankings must use only data available before the month starts. Any
entry rule that is observed after market close is executed on the next trading
day according to the execution model.

## Trigger Rules

| Rule | Type | Description |
| --- | --- | --- |
| `monthly_allocation_window` | `time` | Fire once at the start of each month. |
| `signal_cutoff` | `time` | Signals and rankings may use only data available before the month starts. |
| `next_session_execution` | `condition` | Entry rules observed after market close execute on the next trading day according to the execution model. |

| Setting | Value |
| --- | --- |
| `trigger_frequency` | Monthly |
