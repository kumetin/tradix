# Classic 12-1 Momentum Validation

## Experiment ID

`classic-12-1-momentum-validation`

## Status

`completed`

## Hypothesis

A frozen 12–1 adjusted-price momentum ranking will produce stronger aggregate
forward outcomes for highly ranked stocks than for low-ranked stocks, random
equal-count selections, and the dated equal-weight candidate universe.

At target count 10, the model is also expected to produce positive mean excess
return versus SPY at one or more primary horizons, although SPY outperformance
is not required to establish basic platform correctness.

## Reference Configuration

* [Selection model](../../stages/OPERATIONS.md#selection-and-selection-models):
  [`classic-12-1-momentum`](../../stages/selection-models/classic-12-1-momentum.md)
* Component protocol:
  [`classic-12-1-price-momentum`](../../backtests/components/selection-models/classic-12-1-price-momentum.md)
* [Evaluation plan](../../stages/OPERATIONS.md#evaluation-plans):
  [`classic-12-1-momentum-validation`](../../configuration/evaluations/selection-models/classic-12-1-momentum-validation.md)

## Declared Deltas

Introduce a price-only selection baseline that ranks candidates by adjusted
return from session offset `252` through session offset `21`.

The experiment:

* excludes the most recent 21 sessions from the primary momentum signal;
* applies no fundamental or technical eligibility gates beyond data
  sufficiency;
* ranks all eligible candidates continuously;
* compares target counts 5, 10, 20, and 50;
* compares against random equal-count selection;
* compares against the dated equal-weight universe;
* compares against SPY;
* compares highest, middle, and lowest momentum quintiles; and
* compares against a 12-month momentum variant that includes the latest month.

All model rules, variants, random seeds, evaluation dates, and success criteria
are frozen before
[execution](../../stages/OPERATIONS.md#execution-and-execution-models).

## Evaluation Window

Use the 2016–2020 monthly window and historical membership tape declared by the
referenced evaluation plan. This period predates the selection-model windows
already inspected in this research sequence.

Historical membership is resolved point-in-time. Historical price coverage is
incomplete for some departed and renamed members, so every missing member is
reported as an explicit exclusion. This is a validation-only experiment with
no locked promotion holdout.

## Primary Variant

The primary variant is:

```text
model: classic-12-1-momentum
target_count: 10
decision_frequency: monthly
entry_reference: next-session adjusted open
primary_horizons: 63 and 126 valid sessions
```

## Success Criteria

The platform and model pass the primary validation when all of the following
hold on the declared validation window:

1. At least 500 selected-stock forward observations exist at both 63 and 126
   sessions.
2. At least 90% of dated candidates are either eligible or have an explicit
   recorded exclusion reason.
3. The highest momentum quintile has higher mean forward return than the
   lowest momentum quintile at both 63 and 126 sessions.
4. The highest-minus-lowest quintile spread is positive at both primary
   horizons.
5. Spearman correlation between momentum percentile and forward return is
   positive at both primary horizons.
6. Mean forward return at target count 10 exceeds the mean return of frozen
   random equal-count selections at both primary horizons.
7. The paired decision-date difference versus random selection is positive in
   at least 60% of decision-date and universe groups.
8. No single ticker contributes more than 10% of selected observations.
9. All deterministic ranking, date-alignment, target-weight, and manual
    reconciliation checks pass.

## Benchmark-Outperformance Criteria

Promotion as a benchmark-relative selection baseline additionally requires:

1. Positive mean excess return versus the dated equal-weight universe at both
   63 and 126 sessions.
2. Positive mean excess return versus SPY at either 63 or 126 sessions.
3. Positive SPY-beating paired decision-date difference in at least half of
   decision-date and universe groups at one primary horizon.
4. Positive benchmark-relative performance in more than one calendar year.
5. No single ticker or calendar year explains more than
   half of total excess return.

Failure to beat SPY alone does not establish that the data or platform is
incorrect. Failure of rank ordering, bucket separation, reproducibility, or
manual reconciliation is more directly relevant to platform validation.

## Diagnostic Expectations

The expected aggregate ordering is:

```text
highest momentum quintile
    >
middle momentum quintile
    >
lowest momentum quintile
```

Perfect monotonicity is not required. No more than one adjacent-bucket
inversion is permitted at each primary horizon.

The 12–1 variant is expected to perform at least as well as the variant that
includes the latest month at one or both primary horizons.

Extremely high returns, near-perfect hit rates, or unrealistically stable
outperformance require a mandatory leakage and survivorship review before any
promotion decision.

## Run Index

| Status  | Configuration | Artifact |
| ------- | ------------- | -------- |
| Superseded | `c3ea35b0`; bucket-correlation reporting defect | [`20260723-134522Z__historical-membership-2016-2020__c3ea35b0`](../../artifacts/stock/backtests/components/selection-models/classic-12-1-momentum-validation/20260723-134522Z__historical-membership-2016-2020__c3ea35b0/) |
| Superseded | `c3ea35b0`; before runtime reconciliation assertions | [`20260723-134641Z__historical-membership-2016-2020__c3ea35b0`](../../artifacts/stock/backtests/components/selection-models/classic-12-1-momentum-validation/20260723-134641Z__historical-membership-2016-2020__c3ea35b0/) |
| Superseded | `c3ea35b0`; 73.21% mean price coverage | [`20260723-134753Z__historical-membership-2016-2020__c3ea35b0`](../../artifacts/stock/backtests/components/selection-models/classic-12-1-momentum-validation/20260723-134753Z__historical-membership-2016-2020__c3ea35b0/) |
| Superseded | `8cdd2b6d`; direct-provider repair only | [`20260723-142624Z__historical-membership-2016-2020__8cdd2b6d`](../../artifacts/stock/backtests/components/selection-models/classic-12-1-momentum-validation/20260723-142624Z__historical-membership-2016-2020__8cdd2b6d/) |
| Superseded | `5131ce38`; before internal-gap exclusions | [`20260723-143312Z__historical-membership-2016-2020__5131ce38`](../../artifacts/stock/backtests/components/selection-models/classic-12-1-momentum-validation/20260723-143312Z__historical-membership-2016-2020__5131ce38/) |
| Completed | `511362a9`; repaired data and integrity exclusions | [`20260723-143740Z__historical-membership-2016-2020__511362a9`](../../artifacts/stock/backtests/components/selection-models/classic-12-1-momentum-validation/20260723-143740Z__historical-membership-2016-2020__511362a9/) |

The first rerun corrected a bucket-correlation reporting defect in a
non-signal aggregation path before the economic results were inspected. The
repair did not change the selector, percentiles, bucket membership, forward
returns, model rules, parameters, or success criteria. It was a correctness
repair rather than a strategy change made in response to the observed
outcomes. Later reruns added reconciliation assertions and repaired or
excluded deficient input histories; they likewise did not tune the model from
its results.

## Results

| Variant | Target count | Horizon | Observations | Mean return | Excess vs SPY | Excess vs universe |
| ------- | -----------: | ------: | -----------: | ----------: | ------------: | -----------------: |
| Classic 12-1 | 10 | 63 | 599 | 3.82% | -0.36% | -0.04% |
| Classic 12-1 | 10 | 126 | 599 | 8.68% | 0.15% | 0.68% |
| Classic 12-1 | 10 | 252 | 597 | 24.70% | 6.39% | 7.84% |

The paired mean difference versus 100 frozen random selections was +0.03
percentage points at 63 sessions, +0.75 points at 126 sessions, and +7.84
points at 252 sessions. The decision-level positive rates were respectively
53.33%, 51.67%, and 66.67%.

The primary ranking signature failed:

| Horizon | Weakest quintile | Strongest quintile | High-minus-low spread | Mean decision Spearman |
| ---: | ---: | ---: | ---: | ---: |
| 63 | 4.81% | 3.18% | -1.64% | -0.037 |
| 126 | 9.87% | 6.95% | -2.92% | -0.039 |
| 252 | 19.73% | 16.13% | -3.60% | -0.014 |

Maximum ticker concentration was 6.01%. All 60 decision dates resolved a
historical membership snapshot and every candidate received an eligibility
decision. Direct Yahoo/pure-rename recovery persisted 106 identities and the
FNSPID archive recovered another 69. After excluding ten histories with
internal gaps, usable dated price coverage averaged 94.60% (range 90.49% to
98.20%). Sixty historical identities remain unresolved.

Runtime reconciliation assertions passed for membership/feature cutoffs,
deterministic output, descending ranking, unique instruments, exclusion,
selected counts, weights, and forward date alignment.

## Findings

The top-ten selection produced positive long-horizon benchmark-relative
returns, but the broader cross-sectional evidence ran in the opposite
direction from the preregistered momentum hypothesis. The strongest quintile
underperformed the weakest at every measured horizon.

The reported Spearman statistic correlates `momentum_percentile`, not the
one-based output `rank`, with forward return. A larger percentile denotes
stronger momentum, whereas a larger output rank denotes weaker momentum.
Consequently, the preregistered hypothesis requires a positive
percentile/return correlation (or, equivalently, a negative output-rank/return
correlation). The observed percentile/return correlations were negative and
agree with the bucket results: bucket `1` contains the weakest momentum names,
bucket `5` contains the strongest, and bucket `1` had the higher mean return
at every measured horizon.

The implementation and expanded-data integrity checks passed. Raising usable
coverage from 73.21% to 94.60% narrowed the negative bucket spreads, but did
not reverse their sign. The failed momentum ordering is therefore less likely
to be explained solely by the original coverage gap, although the run is still
not a complete S&P 500 reconstruction.

## Decision

The experiment is complete and its implementation-validation purpose passed:
the selector, ranking direction, percentile and bucket assignment,
point-in-time cutoffs, deterministic output, and forward alignment reconciled.
The reporting and data-integrity repairs did not alter the frozen economic
hypothesis after observing its outcomes.

Do not promote the model from this run. Its economic results missed the
preregistered high-minus-low bucket spread,
momentum-percentile/forward-return correlation, and 63-session random-baseline
criteria. In addition, incomplete historical price coverage prevents this run
from serving as final promotion evidence. This is an economic-evidence
limitation, not a rejected or invalid experiment.

## Follow-up

Retain the selector as a deterministic reusable baseline, but do not replace
the existing momentum-only baseline based on this experiment. Reaching
complete coverage now requires a delisted-security source with corporate-action
and terminal-return data. Do not tune the lookback using the consumed
2016–2020 outcomes.
