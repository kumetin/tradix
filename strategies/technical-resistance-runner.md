# Technical Resistance Runner Strategy

## Thesis

Among sufficiently investable equities, candidates with an intact long-term
trend, strong market-relative performance, and a controlled pullback near
point-in-time support are more likely than weaker candidates to revisit their
recent intermediate-term resistance within the next six months.

The strategy separately predicts that realizing 75% after a 5.21% surge and
offering the remaining 25% at setup resistance captures common favorable
excursions while preserving limited participation in a larger continuation.

## Proposed Market Mechanism

The thesis assumes that gradual information diffusion and institutional
position building can sustain relative strength, while temporary selling toward
rising moving-average or recent-price support creates an entry below the
position's intermediate potential. The recent high represents a visible supply
area for the residual profit target. The fixed holding horizon prevents any
unsold quantity from becoming an indefinite investment.

These mechanisms are hypotheses. Neither a high setup score nor a historical
resistance level guarantees a profitable trade.

## Observable Proxies

All values must be observable at the decision cutoff.

| Thesis concept | Point-in-time proxy |
| --- | --- |
| Intact trend | Adjusted close versus SMA50 and SMA150, SMA50 versus SMA150, and current SMA150 versus its value 21 trading sessions earlier. |
| Market-relative strength | Stock return versus SPY over 63, 126, and 252 trading sessions, plus the stock's 126-session excess-return percentile in the dated candidate set. |
| Controlled pullback | Price within 5% of selected support, RSI(14) between 40 and 60, and mean volume over the latest 20 sessions below the preceding 20-session mean. |
| Support | Highest eligible level at or below 103% of price among SMA20, SMA50, SMA150, and the lowest adjusted low over 63 trading sessions. |
| Reward geometry | Distance from price to the trailing 126-session adjusted intraday high relative to distance from price to selected support. |
| Resistance target | Highest adjusted intraday high observed over the trailing 126 trading sessions. |
| Maximum holding horizon | 126 trading sessions after entry. |

Analyst revisions and fundamental momentum are not part of this strategy. Adding
them would require a separately specified thesis and point-in-time evidence
contract rather than silently treating missing values as neutral.

## Required Strategy Behavior

At each configured decision cycle, using only information available at its
knowledge cutoff:

1. Resolve a point-in-time candidate universe with enough valid history for all
   required features.
2. Score every candidate using the technical score below.
3. Rank candidates by score with a deterministic ticker-ID tie-breaker and emit
   the highest-ranked candidate as a single equal-capital target.
4. Enter no earlier than the next trading session after the decision close.
5. At entry, place a good-until-horizon limit sell for 75% of the original
   filled quantity at 5.21% above the filled entry price.
6. Do not place a price stop-loss.
7. After the first fill, offer the remaining 25% at the point-in-time
   resistance target. If resistance is no higher than the first target, sell
   the remainder at the first target rather than at an inferior price.
8. Do not reset or trail either target.
9. Sell every remaining share at the configured execution point on trading
   session 126 after entry.

The six-month exit applies whether or not the partial target was reached.

## Technical Score

The bounded score is `0–70`:

| Component | Maximum | Required behavior |
| --- | ---: | --- |
| Trend quality | 20 | Add 5 points for each true condition: price above SMA150; SMA150 above its value 21 sessions earlier; price above SMA50; SMA50 above SMA150. |
| Relative strength | 20 | Add 4 points for each of 63-, 126-, and 252-session return exceeding SPY; add `8 ×` the candidate's 126-session excess-return percentile in the same dated universe. |
| Pullback quality | 15 | Add 5 points for each true condition: price within 5% of support; RSI(14) in `[40, 60]`; latest-20-session mean volume below the preceding-20-session mean. |
| Reward geometry | 15 | Add 5 points when price is within 6% of support; add 10, 7, 3, or 0 points when resistance reward divided by price-to-support risk is respectively `>=3`, `>=2`, `>=1`, or `<1`. |

Missing values fail the affected condition and receive zero points. Candidates
without a valid price, support, resistance, or full required warm-up are
ineligible rather than zero-filled or forward-filled.

## Required Component Capabilities

| Pipeline operation | Thesis-preserving requirement |
| --- | --- |
| [Universe model](../stages/OPERATIONS.md#universe-resolution-and-universe-models) | Produces reproducible point-in-time equity membership and excludes instruments lacking required warm-up or outcome-independent investability data. |
| [Selection model](../stages/OPERATIONS.md#selection-and-selection-models) | Implements the technical score, cross-sectional relative-strength percentile, deterministic top-one selection, resistance target, and declared missing-data behavior. |
| [Portfolio policy](../stages/OPERATIONS.md#portfolio-transitions-and-portfolio-policies) | Tracks original filled quantity, emits sequential 75% surge and 25% resistance-sale intents without a stop, and emits mandatory session-126 liquidation. |
| [Execution model](../stages/OPERATIONS.md#execution-and-execution-models) | Prevents fills before decision-close features are knowable and supports next-session entry, resting limit exits, partial-position sales, horizon liquidation, costs, slippage, settlement, and conservative ambiguous-bar handling. |

The current compatible stage descriptors are
[Technical Resistance Score](../stages/selection-models/technical-resistance-score.md),
[Single Position Two Stage Profit Horizon Exit](../stages/portfolio-policies/single-position-two-stage-profit-horizon-exit.md),
and
[Daily-Bar Frictionless Fractional](../stages/execution-models/daily-bar-frictionless-fractional.md).

## Prediction Horizon

The primary prediction is that the selected ticker has favorable target
reachability and risk-adjusted return over 126 trading sessions. Supporting
diagnostics should report first-target-hit probabilities and realized outcomes
over 21, 42, 63, 84, 105, and 126 trading sessions, but those diagnostic
windows do not alter the fixed strategy exit.

## Strategy Parameters

| Parameter | Description |
| --- | --- |
| `target_lookback_days` | Positive trading-day lookback used to define resistance; exploratory value `126`. |
| `first_profit_return` | Entry-relative return for the first profit target; current value `0.0521`. |
| `first_profit_sale_fraction` | Fraction of original filled quantity sold at the first target; current value `0.75`. |
| `second_profit_sale_fraction` | Remaining fraction offered at setup resistance; current value `0.25`. |
| `maximum_holding_days` | Positive trading-session limit after entry; exploratory value `126`. |

Score weights and predicates above define the current strategy identity. They
must not be tuned on a locked holdout.

## Thesis-Preserving Variations

The following may test robustness without changing the thesis:

- point-in-time S&P 500 membership versus a broader dated investable-equity
  universe;
- reasonable predeclared resistance and maximum-holding windows around the
  126-session exploratory values;
- predeclared first-profit thresholds and two-stage sale fractions;
- realistic market-on-open versus volume-weighted next-session entry;
- conservative versus explicit intraday ordering when a daily bar crosses an
  order level;
- transaction-cost, slippage, settlement, and fractional-share assumptions;
  and
- walk-forward, regime, and locked-holdout evaluation plans.

## Thesis-Changing Substitutions

The following require a different strategy definition:

- value, analyst, earnings, or fundamental ranking in place of the technical
  continuation and pullback score;
- buying damaged trends because they appear cheap;
- replacing recent resistance with an analyst target or arbitrary fixed return;
- adding a stop-loss as part of the entry thesis;
- repeatedly resetting the target or holding horizon using future highs;
- retaining the residual position indefinitely; or
- using future membership, features, prices, or outcome data.

## Falsification Criteria

The thesis is materially weakened or falsified if:

- technical score rank lacks a stable positive relationship with forward
  target-hit rate or return;
- top-ranked candidates fail to outperform SPY, the equal-weight dated
  universe, and an unfiltered candidate baseline after costs;
- the two-stage sale fails to outperform full resistance liquidation, the
  prior half-resistance rule, or full six-month holding out of sample;
- performance depends on a few extreme winners, one market regime, current
  constituent bias, or one narrow parameter setting;
- drawdowns or tail losses make the improvement in arithmetic mean
  economically unusable;
- realistic entry timing, gaps, limit fills, costs, or settlement eliminate
  the effect; or
- a locked holdout or a materially different point-in-time universe fails to
  reproduce the result.

The exploratory 25-scenario study used to formulate this strategy is not a
locked holdout. Its dates, batches, score adapter, and exit rules were inspected
and revised iteratively, so the same scenarios cannot provide clean
confirmation of the finalized strategy.

## Pipeline Placement

This strategy follows the
[canonical strategy decision pipeline](README.md#canonical-strategy-decision-pipeline).
The technical score and resistance target constrain selection. Next-session
order timing is enforced by execution. Partial target realization and
mandatory horizon liquidation constrain portfolio-policy behavior. Concrete
[trigger](../stages/OPERATIONS.md#trigger), universe, execution,
[funding](../stages/OPERATIONS.md#funding-profiles), and
[evaluation](../stages/OPERATIONS.md#evaluation-plans) plans belong to
configured backtests.

## Research Lineage

The exploratory analysis implementation and latest generated results are:

- [`scripts/analysis/quantitative_swing_25_scenarios.py`](../scripts/analysis/quantitative_swing_25_scenarios.py)
- `artifacts/stock/backtests/components/setup-evaluators/quantitative-swing-25-scenarios/`

The exploratory no-stop, half-target variant produced a `+4.66%` arithmetic
mean across 25 current-universe-biased scenarios. That figure is hypothesis
formation evidence only. The runner used evaluation-date adjusted close as its
entry price; a canonical strategy backtest must instead use a knowable
next-session execution point.

## Backtests

- [TC-001: Random 50 Universe 1 Monthly Single Position](../backtests/strategies/technical-resistance-runner/tc-001-random-50-universe-1-monthly.md)

## Data Requirements

The strategy requires point-in-time universe membership plus daily adjusted
open, high, low, close, volume, SMA20, SMA50, SMA150, RSI(14), and trailing
63-, 126-, and 252-session return inputs with full warm-up. SPY must be
available over the same dates for relative-strength comparisons. Missing OHLCV
rows are not forward-filled.
