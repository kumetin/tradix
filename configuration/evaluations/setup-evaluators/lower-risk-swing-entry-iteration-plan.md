# Lower-Risk Swing Entry Iteration Plan

## Constant Settings

These settings stay fixed across lower-risk swing-entry setup-evaluator
iterations unless this file is intentionally revised before a new experiment
cycle starts.

| Setting | Value |
| --- | --- |
| [Setup evaluator](../../../stages/OPERATIONS.md#setup-evaluators) | [`lower-risk-swing-entry`](../../../stages/setup-evaluators/lower-risk-swing-entry.md) |
| Backtest spec | [`setup-signal-backtest`](../../../backtests/components/setup-evaluators/setup-signal-backtest.md) |
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

## Iteration Dimensions

Each dimension below can become a parameter grid. Keep the universe and time
splits fixed while sweeping these values.

| Dimension | Candidate values | Purpose |
| --- | --- | --- |
| Universe size | `5-smoke`, `20-fast`, `100-validation` | Separates code checks from statistically useful validation. |
| [Evaluation](../../../stages/OPERATIONS.md#evaluation-plans) cadence | `weekly`, `monthly` | Tests whether signals need frequent refresh or survive slower review cadence. |
| Entry mode | `close_entry`, `limit_entry` | Separates immediate signal quality from generated buy-limit reachability. |
| Horizon set | `5/10/20`, `10/20/40/60`, `60/90/120`, `5/10/20/40/60/90/120` | Tests short signal decay, core swing behavior, and slower winners. |
| Minimum setup score | `70`, `80`, `90` | Tests whether setup attractiveness is monotonic with outcomes. |
| Minimum evidence score | `50`, `70`, `85` | Tests whether data quality filters improve reliability. |
| Entry actions | `buy`, `buy+wait` | Tests strict actionable setups versus broader watchlist signals. |
| Stop model | `current`, `risk-1.25`, `risk-1.5`, `support-atr-1.2`, `support-atr-1.5` | Tests whether current stops are too tight. |
| Take-profit model | `current`, `higher-target` | Tests whether current upside targets are too conservative. `higher-target` requires explicit implementation before use. |

## First Iteration Grid

Start with this grid before adding more dimensions:

| Run group | Universe | Period | Cadence | Horizons | Setup score thresholds | Evidence score thresholds | Entry actions |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Smoke | `5-smoke` | Train/dev | `weekly` | `10`, `20` | `80` | `70` | `buy` |
| Fast sweep | `20-fast` | Train/dev | `weekly` | `10`, `20`, `40`, `60` | `70`, `80`, `90` | `50`, `70`, `85` | `buy` |
| Validation 1 sweep | `100-validation` | Validation 1 | `weekly` | `10`, `20`, `40`, `60`, `90`, `120` | Best train/dev candidates only | Best train/dev candidates only | `buy` |
| Validation 2 sweep | `100-validation` | Validation 2 | `weekly` | `10`, `20`, `40`, `60`, `90`, `120` | Candidates that pass Validation 1 | Candidates that pass Validation 1 | `buy` |
| Locked test | `100-validation` | Locked test | `weekly` | `5`, `10`, `20`, `40`, `60`, `90`, `120` | Final frozen candidate only | Final frozen candidate only | `buy` |

Parallel runs are acceptable inside a run group as long as each run writes to a
distinct artifact directory and records its exact configuration.

## Completed Baseline

The first train/dev baseline is recorded here:

- [Lower-Risk Swing Entry Baseline: Current Stop](../../../experiments/setup-evaluators/lower-risk-swing-entry-baseline-current-stop.md)
- [Lower-Risk Swing Entry Stop-Model Sweep](../../../experiments/setup-evaluators/lower-risk-swing-entry-stop-model-sweep.md)

Decision:

```text
rejected_for_promotion
```

Do not continue tuning stricter `setup_score` or `evidence_score` thresholds
for the current stop model. The next train/dev iteration should test explicit
stop-model variants while keeping the same universe and train/dev period.

The stop-model sweep found that wider stops improved results, with
`support-atr-1.5` performing best, but stop-only changes still underperformed
`SPY` and equal-weight universe exposure. Use `support-atr-1.5` as the
provisional stop model for the next train/dev iteration, not as a promotable
configuration.

## Stop-Model Iteration Grid

Use the same 20-stock non-curated universe and train/dev period.

| Run group | Universe | Period | Cadence | Horizons | Setup score thresholds | Evidence score gate | Stop models |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Stop sweep | `20-fast` | Train/dev | `weekly` | `20`, `40`, `60`, `90`, `120` | `70`, `80` | `70` | `current`, `risk-1.25`, `risk-1.5`, `support-atr-1.2`, `support-atr-1.5` |

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

## Review Checklist

After each run group completes, review:

- Best and worst setup-score buckets by realized return.
- Monotonicity of setup-score buckets.
- Evidence-score buckets and whether evidence quality changes outcomes.
- Close-entry versus limit-entry gap.
- Stop-loss and take-profit hit rates.
- Average max favorable and adverse excursion.
- Benchmark-relative return versus `SPY`.
- Equal-weight universe-relative return.
- Concentration by ticker and sector when sector metadata is available.
- Surprising failures that suggest a missing evaluator rule.

## Next Experiments

Only add these after the first iteration grid is understood:

- Wider stop-loss variants.
- Higher take-profit variants.
- Daily cadence for shorter-term signal decay analysis.
- Random-signal baseline.
- Shuffled-date baseline.
- Market-regime-specific validation windows.
- Sector-neutral universe construction.
