# Classic 12-1 Momentum

Reusable [selection](../OPERATIONS.md#selection-and-selection-models) model.

## ID

`classic-12-1-momentum`

## Stage Type

`selection-model`

## Purpose

Rank stocks using intermediate-term price momentum measured over approximately
the previous twelve months while excluding the most recent month.

The model is intentionally simple and deterministic. It serves as a baseline
for validating adjusted-price history, point-in-time candidate membership,
feature calculation, ranking, and forward-outcome alignment.

## Input Contract

| Field             | Type                                | Required | Meaning                                |
| ----------------- | ----------------------------------- | -------- | -------------------------------------- |
| `as_of`           | trading date or timestamp           | Yes      | Completed decision cutoff.             |
| `candidates`      | ordered instrument IDs              | Yes      | Point-in-time candidate population.    |
| `features`        | map of instrument ID to feature row | Yes      | Price features knowable at the cutoff. |
| `fallback_ticker` | ticker ID or `None`                 | No       | Optional defensive target.             |

The required upstream feature is:

| Feature      | Meaning                                                                      |
| ------------ | ---------------------------------------------------------------------------- |
| `ret_252_21` | Adjusted-close return from session offset `252` through session offset `21`. |

The preferred calculation is:

```text
ret_252_21 = adjusted_close[t - 21]
             / adjusted_close[t - 252]
             - 1
```

Session offsets use valid trading sessions rather than calendar days.
Feature construction, rather than this selector, owns endpoint lookup and
history validation. It must emit a value only when 253 valid rows through
cutoff `t` exist and both endpoint adjusted closes are finite and positive.

## Output Contract

| Field           | Type                                     | Required | Meaning                                       |
| --------------- | ---------------------------------------- | -------- | --------------------------------------------- |
| `as_of`         | trading date or timestamp                | Yes      | Input cutoff echoed.                          |
| `eligibility`   | map of instrument ID to decision/reasons | Yes      | Data-sufficiency decisions.                   |
| `ranking`       | ordered scored candidates                | Yes      | Momentum value, percentile, rating, and rank. |
| `targets`       | ordered ticker/weight pairs              | Yes      | Up to `target_count` equal-weight targets.    |
| `fallback_used` | boolean                                  | Yes      | Whether fallback replaced an empty result.    |

Each eligible ranking row contains:

| Field                 | Meaning                                     |
| --------------------- | ------------------------------------------- |
| `instrument_id`       | Permanent instrument identifier.            |
| `ret_252_21`          | Raw 12–1 momentum return.                   |
| `momentum_percentile` | Cross-sectional percentile in `[0.0, 1.0]`. |
| `rating`              | Integer rating from `0` through `100`.      |
| `rank`                | One-based final deterministic rank.         |

## Behavior

Require a known and finite `ret_252_21` value for each candidate.

Rank eligible candidates by ascending `ret_252_21` to calculate the
cross-sectional momentum percentile:

```text
momentum_percentile =
    ascending_zero_based_position / max(eligible_count - 1, 1)
```

Use `1.0` for a singleton eligible population.

Calculate the published rating as:

```text
rating = round(100 * momentum_percentile)
```

Rank candidates for selection by:

1. descending `ret_252_21`;
2. ascending instrument ID.

Select up to `target_count` candidates and emit equal-weight targets:

```text
target_weight = 1 / selected_count
```

Negative-momentum candidates remain eligible. They receive lower rankings
rather than being removed by a hard momentum threshold.

The model does not use:

* fundamentals;
* market capitalization;
* volatility;
* technical trend filters;
* benchmark-relative strength;
* volume;
* sector constraints; or
* future return information.

## Parameters

| name                | type             | required | default | constraints            | description                             |
| ------------------- | ---------------- | -------- | ------- | ---------------------- | --------------------------------------- |
| `target_count`      | positive integer | No       | `10`    | `>= 1`.                | Maximum selected targets.               |
| `fallback_mode`     | enum             | No       | `empty` | `empty` or `fallback`. | Empty-result behavior.                  |
| `lookback_sessions` | integer          | No       | `252`   | Fixed by descriptor.   | Beginning of momentum interval.         |
| `skip_sessions`     | integer          | No       | `21`    | Fixed by descriptor.   | Recent sessions excluded from momentum. |
| `rating_scale`      | integer          | No       | `100`   | Fixed by descriptor.   | Maximum published rating.               |

`lookback_sessions`, `skip_sessions`, and `rating_scale` are documented
parameters but are frozen by this descriptor. Alternative values require a
different declared model or experiment variant.

## Data Requirements

Requires:

* at least 253 valid adjusted-close rows through cutoff `t` per candidate, so
  both indexed endpoints `t - 252` and `t - 21` exist;
* adjusted prices incorporating splits, dividends, and supported corporate
  actions;
* permanent instrument identifiers;
* point-in-time candidate-universe membership; and
* a completed adjusted close for `as_of`.

The implementation or upstream feature stage must distinguish unavailable
history from a valid zero return.

## Point-in-Time Rules

Use only data observable by `as_of`.

The momentum interval ends at session offset `21`, so the most recent
approximately one trading month is deliberately excluded.

The adjusted closes at offsets `252` and `21` must both be known by `as_of`.

Future bars, future constituent membership, future delisting outcomes, and
revised security classifications must never be passed to selection.

Historical tests must not apply current universe membership retroactively.

## Failure Behavior

The upstream feature stage omits `ret_252_21` when endpoint or history
requirements fail. This selector excludes a candidate and records a reason
when:

* `ret_252_21` is missing;
* `ret_252_21` is not finite;
* no feature row exists; or
* the candidate cannot be matched to its input instrument identifier.

Invalid parameters fail before selection.

If no candidates are eligible:

* `fallback_mode = empty` emits no targets; or
* `fallback_mode = fallback` emits a 100% target to `fallback_ticker`.

`fallback_mode = fallback` fails when `fallback_ticker` is absent.

## Benchmark Contract

Replay identical dated universes and compare the selected stocks with:

* SPY;
* the dated equal-weight candidate universe;
* unfiltered candidates;
* random equal-count selections using frozen random seeds;
* the highest momentum quintile;
* the middle momentum quintile;
* the lowest momentum quintile; and
* a momentum variant that includes the most recent month.

Measure:

* eligible coverage;
* forward returns;
* benchmark-relative returns;
* positive-return and SPY-beating hit rates;
* rank-bucket monotonicity;
* highest-minus-lowest momentum spread;
* ticker and sector concentration; and
* cross-universe consistency.

The primary correctness signature is stronger aggregate forward performance
for high-momentum ranks than for low-momentum ranks. Beating SPY in every
period is not required for implementation correctness.

For correlation reporting, use `momentum_percentile`: a positive correlation
with forward return supports the momentum hypothesis. The one-based output
`rank` runs in the opposite direction (`1` is strongest), so an equivalent
correlation calculated from that field is expected to be negative.

## Implementation

`stages/selection-models/classic_12_1_momentum.py`

Public entry point: `select(...)`.
