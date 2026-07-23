# Classic 12-1 Momentum Historical Validation

[Evaluation](../../../stages/OPERATIONS.md#evaluation-plans)

## Settings

| Setting | Value |
| --- | --- |
| `warmup_start` | `2015-01-02` |
| `evaluation_start` | `2016-01-04` |
| `evaluation_end` | `2020-12-31` |
| `split_method` | Single previously unused validation window; no locked holdout |
| `cadence` | Monthly, final completed SPY session |
| `horizons` | `63`, `126`, `252` valid sessions |
| `universe_source` | Latest historical S&P 500 membership snapshot on or before each cutoff |
| `membership_tape` | `data/stock/universes/sp500-historical-membership.csv` |

Warm-up rows construct the 252-to-21-session signal and are excluded from
reported outcomes. The window predates the
[selection-model](../../../stages/OPERATIONS.md#selection-and-selection-models)
development windows
inspected elsewhere in this repository.

Membership is point-in-time, but local prices do not cover every departed,
renamed, acquired, or delisted historical member. Each decision must report
the full membership count, locally measurable count, missing-price members,
and coverage ratio. Missing members are explicit exclusions, never silently
removed from the denominator.

Because incomplete historical-price coverage can retain survivorship bias,
this plan is validation evidence only and has no locked promotion holdout.
Results must not be described as a complete historical S&P 500 backtest.
