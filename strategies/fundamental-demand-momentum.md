# Fundamental Demand Momentum Strategy

## Thesis

Equities with simultaneously improving reported fundamentals, observable
institutional accumulation, abnormal buying volume, intact long-term trend,
and benchmark-relative strength will have higher forward returns than the
dated equal-weight candidate universe. The effect is expected to be most
useful over roughly 3–18 months, but the horizon and return distribution must
be measured rather than assumed.

## Proposed Mechanism

Improving earnings, revenue, margins, and debt may represent strengthening
business quality. Institutional position building and abnormal up-day volume
may transmit that information into prices gradually, while long-term and
relative momentum identify cases where market demand already confirms rather
than contradicts the reported improvement.

This is a falsifiable hypothesis. The source conversation's 55% win rate,
20%–25% target, 7%–8% stop, and claimed expectancy are not accepted evidence.

## Point-in-Time Observable Proxies

| Concept | Observable proxy |
| --- | --- |
| EPS improvement | Latest reported diluted EPS exceeds the comparable year-ago quarter. |
| Margin expansion | Latest reported quarterly net margin exceeds the comparable year-ago quarter. |
| Revenue improvement | Latest reported revenue exceeds the comparable year-ago quarter. |
| Debt improvement | Latest reported total debt is below the comparable year-ago quarter. |
| Institutional accumulation | Latest available aggregate reported institutional share change is positive. |
| Abnormal buying volume | Up close with volume at least 1.5 times the mean of the prior 50 valid rows. |
| Long-term trend | Adjusted close above SMA200. |
| Relative strength | Trailing 252-row return above SPY over the same cutoff. |

Quarterly values become observable on `available_date`, not fiscal period end.
The current proxies test improvement, not the stronger unimplemented claim of
multi-quarter acceleration.

## Prediction Horizon

Primary forward outcomes are measured at 63, 126, 252, and 378 trading
sessions. A 15-session diagnostic measures stagnation and opportunity cost.
No data window is a strategy parameter.

## Required Component Behavior

At each weekly [trigger](../stages/OPERATIONS.md#trigger):

1. Resolve a reproducible point-in-time investable universe.
2. Supply market and fundamental evidence through the completed cutoff using
   the [market-data service](../stages/OPERATIONS.md#market-data-resolution).
3. Require all eight proxies and rank eligible stocks by 252-session return,
   then relative volume, using the
   [Fundamental Technical Momentum selection model](../stages/selection-models/fundamental-technical-momentum.md).
4. Express the selected targets through a
   [portfolio policy](../stages/OPERATIONS.md#portfolio-transitions-and-portfolio-policies).
5. Use an [execution model](../stages/OPERATIONS.md#execution-and-execution-models)
   that prevents same-close fills and models stops, gaps, costs, settlement,
   and partial quantities.

The proposed exit expression is
[Partial Profit Breakeven Time Exit](../stages/portfolio-policies/partial-profit-breakeven-time-exit.md).
It is a strategy configuration to compare against simpler policies, not proof
of the selection thesis.

## Strategy Parameters

| Parameter | Description |
| --- | --- |
| `selection_target_count` | Positive count of ranked eligible targets emitted per decision. |

The eight proxy definitions are currently part of the thesis identity.
 [Funding](../stages/OPERATIONS.md#funding-profiles), trigger, universe,
execution, accounting, and
[evaluation](../stages/OPERATIONS.md#evaluation-plans) settings are
runner configuration rather than strategy parameters.

## Required Component Capabilities

| Pipeline operation | Requirement |
| --- | --- |
| [Universe model](../stages/OPERATIONS.md#universe-resolution-and-universe-models) | Point-in-time membership and sufficient market/fundamental coverage without current-constituent leakage. |
| [Selection model](../stages/OPERATIONS.md#selection-and-selection-models) | All-of eligibility, deterministic relative-momentum ranking, target count/weights, and explicit missing-data behavior. |
| [Portfolio policy](../stages/OPERATIONS.md#portfolio-transitions-and-portfolio-policies) | Preserve target intent while managing partial exits, protective stops, stagnation, and horizon state. |
| [Execution model](../stages/OPERATIONS.md#execution-and-execution-models) | Next-session fills, conservative ambiguous-bar ordering, gap-through stops, costs, partial shares, and settlement. |

## Thesis-Preserving Variations

- predeclared target counts;
- weekly versus monthly decision frequency;
- reasonable predeclared definitions of abnormal volume and relative strength;
- strict all-of eligibility versus a predeclared minimum-condition count;
- point-in-time S&P 500 versus broader dated investable US equities;
- immediate next-session entry versus a precisely defined, independently
  tested consolidation breakout; and
- simpler portfolio policies compared with the proposed partial-profit policy.

## Thesis-Changing Substitutions

- value or analyst-target ranking in place of improvement and demand;
- using current fundamentals or ownership to rewrite historical decisions;
- treating missing evidence as a passing condition;
- buying weak relative momentum or a broken long-term trend while attributing
  the result to this thesis; or
- optimizing solely for a target backtest win rate or advertised expectancy.

## Falsification Criteria

The thesis is weakened or rejected if:

- eligible stocks do not beat both SPY and the dated equal-weight universe
  after costs;
- the all-of group does not outperform technical-only, fundamental-only, and
  leave-one-condition-out baselines;
- results depend on a few securities, current-constituent bias, one market
  regime, or one narrow threshold;
- missing fundamental or ownership coverage explains apparent selectivity;
- turnover, gaps, stops, or settlement eliminate the effect;
- expectancy is driven by an unacceptable drawdown or rare extreme winners;
  or
- a locked holdout or materially different point-in-time universe fails.

Any rule changed after viewing a holdout makes that period contaminated.

## Pipeline Placement

The strategy follows the
[canonical strategy decision pipeline](README.md#canonical-strategy-decision-pipeline).
Fundamental, demand, trend, and relative-strength rules belong to selection.
Partial targets and stops belong to portfolio policy. Fill timing and costs
belong to execution.

## Data Requirements

Canonical local inputs and point-in-time derived outputs are:

```text
data/stock/prices/daily/<year>/<ticker>.csv
data/stock/fundamentals/quarterly/<available-year>/<ticker>.csv
data/stock/institutions/quarterly/<available-year>/<ticker>.csv
data/stock/features/daily/<year>/<ticker>.csv
```

The fundamental fetcher and enrichment pipeline provide the required reported
facts and derived flags. Historical evaluation also requires point-in-time
universe membership; the current-universe dataset alone is biased.
