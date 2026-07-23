# Lower-Risk Swing Entry Iteration Plan

## Constant Settings

These settings stay fixed across lower-risk swing-entry setup-evaluator
iterations unless this file is intentionally revised before a new experiment
cycle starts.

| Setting | Value |
| --- | --- |
| [Setup evaluator](../../../stages/OPERATIONS.md#setup-evaluators) | [`lower-risk-swing-entry`](../../../stages/setup-evaluators/lower-risk-swing-entry.md) |
| Component benchmark | [`setup-evaluator-forward-outcome-benchmark`](../../../backtests/components/setup-evaluators/setup-evaluator-forward-outcome-benchmark.md) |
| Backtest type | `isolated component backtest` |
| Price basis | Local daily adjusted OHLCV and derived feature rows |
| `warmup_start` | `2014-01-01` |
| `evaluation_start` | `2015-01-01` |
| `evaluation_end` | `2026-06-30` |
| `split_method` | Train/dev plus two validation windows and locked holdout |
| `train_period` | `2015-01-01` to `2019-12-31` |
| `validation_1_period` | `2020-01-01` to `2021-12-31` |
| `validation_2_period` | `2022-01-01` to `2023-12-31` |
| `locked_test_period` | `2024-01-01` to `2026-06-30` |
| Benchmark | `SPY` |
| Secondary baseline | Equal-weight evaluated universe exposure |
| Default cadence | `weekly` |
| Default horizons | `10`, `20`, `40`, `60` trading days |
| Extended horizons | `90`, `120` trading days |
| Default entry actions | `buy` |

Warm-up rows are available only to initialize rolling indicators. Do not include
warm-up-only dates in reported performance metrics.

## Split Rules

- Use the train/dev period for frequent iteration and debugging.
- Use Validation 1 only after a candidate configuration looks promising on
  train/dev.
- Use Validation 2 only after the candidate survives Validation 1.
- Do not use the locked test period during ordinary tuning.
- If a locked-test result changes evaluator rules, thresholds, universe choice,
  or outcome-model assumptions, that locked period is no longer clean for that
  configuration family.
- Preserve losing and inconclusive runs, not only winning runs.

## Universe-Size Guidance

| Universe size | Use | Interpretation |
| --- | --- | --- |
| `5` stocks | Smoke/debug only | Confirms the run completes and artifacts look sane. Do not infer signal quality. |
| `20` stocks | Fast train/dev iteration | Useful for finding obvious problems, but ticker concentration can dominate results. |
| `100+` stocks | Validation and serious comparison | Minimum useful size before trusting setup-score or threshold conclusions. |

Prefer non-curated, sector-diverse universes for validation. A highly curated
high-momentum universe can make the evaluator look better than it is.

## Promotion Criteria

A configuration is worth promoting from train/dev to validation only if most of
these are true:

- Higher `setup_score` buckets show better realized returns or lower adverse
  excursion than lower buckets.
- `buy` signals outperform `SPY` and equal-weight universe exposure across more
  than one horizon.
- Results are not explained by one ticker, one sector, or one short market
  regime.
- Stop-loss rate is not high enough to erase otherwise good forward returns.
- Limit-entry [trigger](../../../stages/OPERATIONS.md#trigger) rate is high enough that the trade plan is reachable.
- Evidence-score filtering improves consistency without removing nearly all
  trades.
