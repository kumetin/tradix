# Classic 12-1 Momentum Validation

Isolated [selection](../../../stages/OPERATIONS.md#selection-and-selection-models)
benchmark.

## Component Under Test

Component type:
[`selection-model`](../../../stages/selection-models/README.md)

[Classic 12-1 Momentum](../../../stages/selection-models/classic-12-1-momentum.md)

## Question

Does a frozen 12–1 adjusted-price momentum rank identify stocks with stronger
forward outcomes than SPY, the dated equal-weight universe, random selection,
and lower-ranked momentum candidates?

## Backtest Type

`isolated component backtest`

## Direct Input/Output Contract

Input is each dated point-in-time universe and the adjusted-price feature rows
knowable at the completed decision cutoff.

Output is:

* data-sufficiency eligibility;
* raw `ret_252_21`;
* momentum percentile;
* integer rating;
* deterministic ranking; and
* equal-weight targets.

Future bars score outputs only after selection.

No portfolio state, existing positions, transaction costs, portfolio policy,
or execution model is passed to the component under test.

## Decision Schedule

The default protocol evaluates one decision after the final completed trading
session of each calendar month.

A weekly schedule may be declared by an experiment, but weekly and monthly
results must not be combined in the same aggregate summary.

All variants in one experiment must use identical decision dates.

The registered
[evaluation](../../../stages/OPERATIONS.md#evaluation-plans)
[plan](../../../configuration/evaluations/selection-models/classic-12-1-momentum-validation.md)
uses monthly decisions from 2016 through 2020 and resolves the latest
historical S&P 500 membership snapshot on or before each cutoff.

## Variants

Compare:

* classic 12–1 momentum;
* 12-month momentum including the latest month;
* 6–1 momentum;
* random equal-count selection using frozen random seeds;
* highest momentum quintile;
* middle momentum quintile;
* lowest momentum quintile; and
* unfiltered dated-universe outcomes.

Evaluate target counts:

* `5`;
* `10`;
* `20`; and
* `50`.

The primary variant is classic 12–1 momentum at target count `10`.

Variant definitions and target counts must be declared before results are
inspected.

## Outcome Model

Use next-session adjusted open as the observable entry reference.

Measure adjusted-close outcomes over:

* `21` valid sessions;
* `63` valid sessions;
* `126` valid sessions; and
* `252` valid sessions.

For decision cutoff `t`, entry session `e = t + 1`, and horizon `h`:

```text
forward_return_h =
    adjusted_close[e + h]
    / adjusted_open[e]
    - 1
```

Calculate the matching SPY and dated equal-weight-universe returns using the
same decision date, entry session, price convention, and outcome horizon.

No
[portfolio policy](../../../stages/OPERATIONS.md#portfolio-transitions-and-portfolio-policies)
or
[execution model](../../../stages/OPERATIONS.md#execution-and-execution-models)
is applied.

Also measure maximum adverse excursion and maximum favorable excursion between
the entry reference and each outcome horizon.

Warm-up rows initialize features but are excluded from reported observations.

## Bucket Evaluation

Divide eligible candidates into five approximately equal-sized momentum
buckets for each decision date.

Bucket `1` contains the weakest momentum candidates.

Bucket `5` contains the strongest momentum candidates.

Publish:

* mean and median forward return by bucket;
* excess return versus SPY by bucket;
* excess return versus the dated universe by bucket;
* observation count by bucket;
* highest-minus-lowest bucket spread; and
* Spearman correlation between momentum percentile and forward return.

Bucket evaluation uses all eligible candidates and is independent of
`target_count`.

## Baselines

Use:

* SPY;
* dated equal-weight candidate universe;
* unfiltered eligible candidates;
* random equal-count selections with at least 100 frozen seeds;
* lowest momentum quintile;
* middle momentum quintile;
* highest momentum quintile; and
* momentum including the latest month.

Random selections must be sampled independently for each decision date from
the same eligible candidate set available to the momentum model.

## Metrics

Report:

* eligible candidate count;
* eligibility coverage;
* selected count;
* selection frequency;
* mean and median forward return;
* excess return versus SPY;
* excess return versus the dated equal-weight universe;
* positive-return hit rate;
* SPY-beating hit rate;
* universe-beating hit rate;
* maximum adverse excursion;
* maximum favorable excursion;
* highest-minus-lowest momentum-bucket spread;
* rank-bucket monotonicity;
* Spearman rank correlation;
* paired decision-date difference versus random selection;
* paired decision-date difference versus the dated universe;
* concentration by ticker;
* concentration by sector when point-in-time sector classifications are
  available, otherwise an explicit `N/A`;
* concentration by decision year;
* concentration by candidate universe;
* implied turnover between consecutive target sets; and
* bootstrap confidence intervals for primary mean differences.

Every aggregate metric must include its observation count.

## Data-Reconciliation Checks

For every decision date, assert:

```text
feature_end <= as_of
membership_effective_at <= as_of
entry_session > as_of
outcome_session > entry_session
```

Also verify:

* one ranking row per eligible instrument;
* no duplicate permanent instrument IDs;
* excluded instruments are absent from ranking and targets;
* ranking is monotonically descending by `ret_252_21`;
* tied scores resolve by ascending instrument ID;
* selected count equals `min(target_count, eligible_count)`;
* target weights sum to `1.0` within numerical tolerance;
* no future-return column is available to selection code;
* repeated execution with the same immutable inputs is identical; and
* stock, SPY, and universe outcomes use identical date alignment.

## Manual Audit Sample

Persist a manually inspectable sample for each run containing at least:

* three selected candidates;
* three eligible non-selected candidates;
* two excluded candidates;
* one split or dividend case when available;
* one ticker-change case when available; and
* one universe addition or removal case when available.

For each sampled candidate, store:

* permanent instrument ID;
* ticker at cutoff;
* membership evidence;
* cutoff session;
* adjusted close at `t - 252`;
* adjusted close at `t - 21`;
* manually recomputed `ret_252_21`;
* stored `ret_252_21`;
* percentile;
* rating;
* rank;
* selection status;
* next-session adjusted open;
* horizon adjusted close;
* stock forward return;
* SPY forward return; and
* excess return.

## Interpretation Rules

A successful implementation should generally produce:

```text
strongest momentum bucket
    >
dated equal-weight universe
    >
weakest momentum bucket
```

This ordering is expected in aggregate over a sufficiently broad sample, not
on every decision date or at every horizon.

Do not reject the implementation solely because the top selection fails to
beat SPY in one evaluation period.

Investigate the platform or data when:

* high and low momentum buckets show no meaningful separation;
* the ranking direction appears reversed;
* results change between identical runs;
* returns are implausibly strong;
* present-day universe membership materially improves historical results;
* corporate-action cases fail manual reconciliation;
* SPY and stock returns use different entry dates; or
* selected observations disappear without recorded exclusion reasons.

Implausibly strong performance is a possible indication of look-ahead bias,
survivorship bias, stale constituents, or incorrect price adjustment.

## Output Location

Store immutable configuration, eligibility, ranking, targets, outcomes,
summaries, paired comparisons, audit samples, and an execution report under:

```text
artifacts/stock/backtests/components/selection-models/classic-12-1-momentum-validation/<run-directory>/
```

Expected files include:

```text
configuration.json
input-lineage.json
coverage.csv
ranking.csv
targets.csv
forward-outcomes.csv
random-cohorts.csv
bucket-summary.csv
benchmark-summary.csv
paired-comparisons.csv
concentration-summary.csv
audit-samples.csv
execution-report.json
README.md
```
