# Configuration Profiles

This directory is the single home for reusable declarative inputs and run
context that do not produce independently attributable performance outputs.

Configuration profiles are selectable run bindings, but they are not reusable
stages. Validate their schemas, dates, references, and deterministic application;
compare their effects only through controlled configured-strategy backtests.

## Profile Families

- [Triggers](triggers/README.md) follow the canonical
  [trigger responsibility](../stages/OPERATIONS.md#trigger).
- [Static Universes](universes/README.md) follow the canonical
  [universe responsibility](../stages/OPERATIONS.md#universe-resolution-and-universe-models).
- [Funding](funding/README.md) follows the canonical
  [funding responsibility](../stages/OPERATIONS.md#funding-profiles).
- [Evaluations](evaluations/README.md) follows the canonical
  [evaluation-plan responsibility](../stages/OPERATIONS.md#evaluation-plans).

Future declarative benchmark sets, market-data provider profiles, and calendars
should live under this directory rather than becoming root-level profile
directories.

Behavior with independently attributable output belongs under [`stages/`](../stages/README.md).
The distinction and testing layers are defined in
[Strategy Operations and Stage Responsibilities](../stages/OPERATIONS.md).
