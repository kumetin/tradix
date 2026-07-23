# Momentum Rotation Strategy

## Thesis

Among sufficiently investable equities, intermediate relative momentum tends to
persist when the broader price trend remains intact. A bounded short-term
pullback within that intact trend may improve entry price without eliminating
the expected continuation effect.

The strategy therefore predicts that, over the next allocation period, the
strongest eligible candidates will outperform weaker candidates and the
equal-weight candidate universe. It separately predicts that a short,
time-bounded pullback entry will improve risk-adjusted entry outcomes relative
to immediate entry without an unacceptable missed-entry rate.

## Proposed Market Mechanism

The thesis assumes that information diffusion, institutional position building,
and investor underreaction can produce price continuation across intermediate
horizons. Trend-health and rolling-drawdown constraints distinguish plausible
continuation from severely impaired price structures. The entry rule assumes
that some short-term selling inside an intact trend is transient rather than a
reversal.

These mechanisms are hypotheses, not established facts. The [evaluation plan](../stages/OPERATIONS.md#evaluation-plans)
must test their observable predictions rather than infer validity from total
portfolio return alone.

## Observable Proxies

| Thesis concept | Point-in-time proxy |
| --- | --- |
| Intermediate relative momentum | Trailing adjusted-price return ranked across the same dated candidate set. |
| Intact broader trend | Current price or medium-term SMA above the long-term SMA. |
| Absence of structural damage | Drawdown from the trailing rolling high remains above a configured floor. |
| Short countertrend pullback | Configured number of consecutive down closes after [selection](../stages/OPERATIONS.md#selection-and-selection-models). |
| Opportunity expiry | End of the current allocation cycle. |

The proxies are part of the strategy identity. Replacing them with unrelated
value, mean-reversion, analyst-revision, or fundamental-quality signals creates
a different market thesis and therefore a different strategy.

## Required Strategy Behavior

At each configured decision cycle, using only information available at its
knowledge cutoff:

1. Resolve a point-in-time candidate universe.
2. Apply broader-trend and rolling-drawdown eligibility rules.
3. Rank eligible candidates by intermediate trailing return.
4. Emit one or more of the strongest candidates as target intent.
5. Wait for the bounded short-term pullback condition.
6. Enter on the next trading session after a confirmed pullback, or apply the
   declared cycle-expiry behavior if no pullback occurs.

The number and weights of targets may vary without changing the thesis. The
[selection model](../stages/OPERATIONS.md#selection-and-selection-models) must
still preserve the required eligibility and momentum-rank
semantics.

## Required Component Capabilities

| Pipeline operation | Thesis-preserving requirement |
| --- | --- |
| [Universe model](../stages/OPERATIONS.md#universe-resolution-and-universe-models) | Produces reproducible point-in-time membership with enough history for every required proxy. |
| [Selection model](../stages/OPERATIONS.md#selection-and-selection-models) | Implements broader-trend eligibility, rolling-high drawdown eligibility, intermediate trailing-return ranking, the bounded consecutive-down-close pullback, deterministic target construction, and declared opportunity-expiry/no-eligible-candidate behavior. |
| [Portfolio policy](../stages/OPERATIONS.md#portfolio-transitions-and-portfolio-policies) | Can consume the selection model's single- or multi-target intent without changing its rank order. |
| [Execution model](../stages/OPERATIONS.md#execution-and-execution-models) | Prevents fills before the signal is knowable and accounts for the configured costs and settlement constraints. |

The current compatible selection implementations are
[SMA Drawdown Trailing Return](../stages/selection-models/sma-drawdown-trailing-return.md)
and
[Top N SMA Drawdown Trailing Return](../stages/selection-models/top-n-sma-drawdown-trailing-return.md).

## Signal Qualification Rule

After selection, wait for the configured number of consecutive down closes:

```text
close day 1 > close day 2 > ... > close day N
```

The condition becomes knowable only after the final close. The earliest valid
simulated fill is therefore the next trading session's adjusted open. If the
condition does not occur before the allocation cycle expires, apply the
configured `entry_fallback`.

## Prediction Horizon

The present backtests reevaluate monthly, so the primary prediction horizon is
one allocation cycle. Longer holding periods caused by unchanged selection or
portfolio policy are portfolio-expression outcomes and must not silently
replace the monthly signal-quality test.

## Strategy Parameters

| Parameter | Description |
| --- | --- |
| `entry_down_days` | Positive number of consecutive down closes representing a bounded short-term pullback. |
| `entry_fallback` | Declared action when no pullback occurs before opportunity expiry. |

Trend, drawdown, momentum-window, and target-count values are declared by the
compatible selection-model instance. They are experimental parameters of the
thesis implementation, not permission to replace its required semantics.

## Thesis-Preserving Variations

The following may test robustness without creating a different strategy:

- point-in-time S&P 500 versus a broader investable-equity universe;
- reasonable momentum, SMA, rolling-high, and pullback windows declared before
  evaluation;
- one target versus several top-ranked targets;
- new-money allocation, concentrated rotation, or diversified rotation;
- different [funding](../stages/OPERATIONS.md#funding-profiles) schedules, costs, slippage, settlement, and fractional-share
  assumptions; and
- full-period, walk-forward, regime, or locked-holdout evaluation plans.

These variations can materially change portfolio results. They preserve the
strategy only while the same continuation and pullback predictions remain the
claims under test.

## Thesis-Changing Substitutions

The following require a different strategy definition:

- ranking by valuation, analyst opinion, fundamental quality, mean reversion,
  or another non-momentum forecast;
- removing both trend health and structural-drawdown controls;
- selecting expected losers or buying because a trend is damaged;
- using future constituent, price, fundamental, or feature information; or
- replacing the bounded pullback premise with an unrelated entry thesis while
  still attributing results to this strategy.

## Falsification Criteria

Evidence against the strategy includes:

- momentum rank lacks a stable positive relationship with forward relative
  return;
- top-ranked eligible candidates fail to outperform the equal-weight dated
  universe after costs;
- trend or drawdown eligibility adds no reproducible benefit over an otherwise
  identical momentum-only baseline;
- pullback-delayed entry fails to improve entry outcomes versus immediate entry,
  or misses enough continuation moves to erase its benefit;
- results depend on current-constituent leakage, one narrow parameter setting,
  a few securities, or one market regime;
- results fail on locked holdouts or materially different point-in-time
  universes; or
- realistic turnover, execution costs, and settlement eliminate the effect.

Changing the rules after observing a locked holdout invalidates that period as
clean falsification evidence.

## Pipeline Placement

This strategy follows the
[canonical strategy decision pipeline](README.md#canonical-strategy-decision-pipeline).
The momentum and trend rules constrain selection. The pullback rule owns the
entry-decision operation. Concrete universe, portfolio, execution, funding, and
evaluation plans are experimental bindings rather than the thesis itself.

## Backtests

- [TC-001: Point-in-Time S&P 500 New-Money Allocation](../backtests/strategies/momentum-rotation/tc-001-point-in-time-sp500.md)
- [TC-002: Investable US Equities Single-Position Rotation](../backtests/strategies/momentum-rotation/tc-002-investable-us-equities-single-position.md)
- [TC-003: Investable US Equities Multi-Position Initial Only](../backtests/strategies/momentum-rotation/tc-003-investable-us-equities-multi-position-initial-only.md)

## Data Requirements

The strategy requires point-in-time universe membership and daily adjusted
price, open, close, rolling-high, moving-average, drawdown, and trailing-return
features with enough warm-up history. Raw and derived local paths are:

```text
data/stock/prices/daily/<year>/<ticker>.csv
data/stock/features/daily/<year>/<ticker>.csv
```
