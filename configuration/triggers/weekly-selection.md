# Weekly Selection

Generates one [selection](../../stages/OPERATIONS.md#selection-and-selection-models)
opportunity after the final completed session of each
configured trading week.

Signals may use only values knowable at that close. Orders derived from those
signals are submitted afterward and may fill no earlier than the next valid
session according to the [execution model](../../stages/OPERATIONS.md#execution-and-execution-models).
The signal cutoff therefore includes only data available before order
submission.

## [Trigger](../../stages/OPERATIONS.md#trigger) Rules

| Rule | Type | Description |
| --- | --- | --- |
| `weekly_selection_window` | `time` | Fire once after the final completed session of each trading week. |
| `signal_cutoff` | `time` | Exclude publications, ownership snapshots, and bars not knowable by the completed close. |
| `next_session_execution` | `condition` | Post-close decisions may fill no earlier than the next valid session. |

| Setting | Value |
| --- | --- |
| `trigger_frequency` | Weekly |
| `signal_cutoff` | Final completed session close |
