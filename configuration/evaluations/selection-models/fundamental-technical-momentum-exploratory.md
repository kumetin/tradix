# Fundamental Technical Momentum Exploratory
[Evaluation](../../../stages/OPERATIONS.md#evaluation-plans)

## Settings

| Setting | Value |
| --- | --- |
| `warmup_start` | `2020-07-01` |
| `evaluation_start` | `2021-07-06` |
| `evaluation_end` | `2025-01-31` |
| `split_method` | Three exploratory development regime windows |

## Windows

| Partition | Start | End | Purpose |
| --- | --- | --- | --- |
| `development-2021-2022` | `2021-07-06` | `2022-12-30` | Initial observable-fundamental period and declining-market regime. |
| `development-2023-2024h1` | `2023-01-03` | `2024-06-28` | Distinct rising-market development regime. |
| `development-2024h2-2025m1` | `2024-07-01` | `2025-01-31` | Recent exploratory regime with 378-session outcome coverage. |

## Sampling

Use the last completed SPY trading session in each ISO week as the decision
cutoff. The next valid session for each instrument supplies adjusted entry
open. Warm-up history may initialize features but is excluded from outcomes.

## Holdout Policy

All three windows are exploratory development partitions. None is a locked
holdout. Results may motivate a future separately frozen validation plan.

## Bias

The configured random S&P 500 universes contain current constituents and carry
current-universe and survivorship bias.
