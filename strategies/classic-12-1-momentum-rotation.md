# Classic 12-1 Momentum Rotation Strategy

## Thesis

Among liquid equities in a point-in-time broad-market universe,
intermediate-term winners tend to continue outperforming over subsequent
months. Ranking on the prior twelve months while omitting the latest month
reduces contamination from short-term reversal.

The strategy predicts that a periodically refreshed, diversified portfolio of
the strongest 12–1 momentum names will earn a positive return after realistic
rotation mechanics and outperform weaker momentum names and the dated
equal-weight candidate universe over complete market cycles.

## Proposed Market Mechanism

Information may diffuse gradually as institutions build positions and
investors underreact to persistent changes in business prospects. This can
create continuation over intermediate horizons. Omitting the latest month
allows transient reversals, liquidity shocks, and very recent price pressure
to decay before the signal is acted upon.

Diversification is portfolio expression rather than a separate source of
predictability. It limits dependence on one extreme winner while retaining
exposure to the cross-sectional signal.

## Observable Point-in-Time Proxies

| Thesis concept | Observable proxy |
| --- | --- |
| Intermediate momentum | Adjusted-close return from session offset `252` through offset `21`. |
| Relative signal strength | Percentile of that return within the dated eligible candidate set. |
| Strongest candidates | Highest percentiles under deterministic descending rank. |
| Continuation | Subsequent total return and excess return over the next one or more allocation cycles. |
| Implementation drag | Turnover, settlement cash, fees, slippage, and missed exposure recorded by execution. |

## Prediction Horizon

The primary prediction horizon is three to twelve months. The portfolio is
reviewed monthly so it can refresh stale ranks, but a continuing holding need
not be sold merely because another decision cycle begins.

## Required Strategy Behavior

At each decision cycle, using only information observable at the completed
cutoff:

1. Resolve a point-in-time equity universe.
2. Exclude candidates without sufficient valid adjusted-price history.
3. calculate 12–1 momentum from offsets `252` and `21`;
4. rank eligible candidates from strongest to weakest;
5. emit a diversified set of the strongest candidates at equal weights; and
6. rotate the portfolio toward those weights under the bound settlement and
   execution rules.

There is no price-trend, volatility, fundamental, sector, or short-term entry
filter in the strategy thesis. Negative-momentum candidates remain rankable.

## Required Component Capabilities

| Pipeline operation | Thesis-preserving requirement |
| --- | --- |
| [Universe resolution](../stages/OPERATIONS.md#universe-resolution-and-universe-models) | Reproduces dated membership without current-constituent leakage. |
| [Selection](../stages/OPERATIONS.md#selection-and-selection-models) | Implements valid-session 12–1 adjusted-price momentum, deterministic cross-sectional ranking, and equal-weight top-target intent. |
| [Portfolio transition](../stages/OPERATIONS.md#portfolio-transitions-and-portfolio-policies) | Sells names leaving the target set and moves continuing and new positions toward supplied target weights. |
| [Execution](../stages/OPERATIONS.md#execution-and-execution-models) | Prevents same-close look-ahead and records costs, settlement, fills, and cash drag. |

The compatible selector is
[Classic 12-1 Momentum](../stages/selection-models/classic-12-1-momentum.md).

## Strategy Parameters

The strategy owns no tunable signal parameter in its initial form. The
`252`-session lookback, `21`-session skip, and percentile direction are frozen
by the selector. Target count is portfolio expression and must be declared by
each configured scenario.

## Thesis-Preserving Variations

- a point-in-time large-cap universe or a broader point-in-time investable
  equity universe;
- monthly or quarterly refresh;
- reasonable diversified target counts declared before evaluation;
- equal-weight rotation with different realistic cost and settlement models;
- an absolute-momentum fallback tested as a separately declared risk-control
  variation; and
- walk-forward, regime, international-market, and untouched holdout tests.

## Thesis-Changing Substitutions

- using the latest month in the primary signal;
- ranking on fundamentals, analyst opinions, volatility, or mean reversion;
- adding trend, quality, sector, or market-regime gates and attributing the
  resulting edge solely to classic 12–1 momentum;
- selecting low-momentum names; or
- using future prices, constituent membership, or corporate-action knowledge.

These may be worthwhile strategies, but they test different mechanisms.

## Falsification Criteria

The thesis is materially weakened when:

- high momentum percentiles do not have a stable positive relationship with
  forward returns;
- the strongest bucket fails to outperform the weakest and the dated
  equal-weight universe across independent periods;
- a top-target portfolio does not produce positive after-cost returns over a
  sufficiently long confirmation window;
- SPY and the dated equal-weight universe explain the apparent profitability;
- performance depends on a few securities, one regime, survivorship, or
  incomplete delisting returns; or
- turnover, execution costs, settlement cash, or taxes plausibly eliminate the
  effect.

An isolated profitable backtest is evidence, not proof. Parameters must not be
changed after inspecting a locked
[evaluation](../stages/OPERATIONS.md#evaluation-plans) holdout and then
retested on that same period.

## Pipeline Placement

This strategy follows the
[canonical strategy decision pipeline](README.md#canonical-strategy-decision-pipeline).
The 12–1 calculation, eligibility, ranking, target count, target weights, and
fallback behavior belong to selection. Rotation belongs to portfolio policy;
fills and settlement belong to execution.

## Backtests

- [TC-001: Point-in-Time S&P 500 Top-10 Monthly Rotation](../backtests/strategies/classic-12-1-momentum-rotation/tc-001-point-in-time-sp500-top-10.md)
- [TC-002: 2015-2020 Temporal Replication](../backtests/strategies/classic-12-1-momentum-rotation/tc-002-point-in-time-sp500-2015-2020-replication.md)

## Data Requirements

The strategy requires effective-dated universe membership, permanent security
identifiers, and split- and dividend-adjusted daily prices with at least 253
valid sessions before each decision cutoff. Delisted and renamed securities
must retain corporate-action and terminal-return history.
