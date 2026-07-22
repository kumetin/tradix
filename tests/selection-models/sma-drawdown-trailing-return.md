# Component Test: SMA Drawdown Trailing Return

Components:

- [SMA Drawdown Trailing Return](../../stages/selection-models/sma-drawdown-trailing-return.md)
- [Top N SMA Drawdown Trailing Return](../../stages/selection-models/top-n-sma-drawdown-trailing-return.md)

## Purpose

Verify that the [selection model](../../stages/OPERATIONS.md#selection-and-selection-models) applies eligibility, ranking, target-count, and
fallback behavior without look-ahead bias.

## Expected Behavior

| Case | Given | Expected |
| --- | --- | --- |
| Eligibility pass | Ticker has `price > long_sma` and drawdown above threshold | Ticker is eligible. |
| Trend pass | Ticker has `medium_sma > long_sma` and drawdown above threshold | Ticker is eligible even if price is below long SMA. |
| Drawdown fail | Ticker fails `drawdown > max_drawdown` | Ticker is ineligible. |
| Ranking | Multiple eligible tickers with different trailing returns | Highest trailing return wins for single-target model. |
| Top N ranking | More eligible tickers than `target_count` | Top `target_count` by trailing return are selected. |
| Fewer than N | Fewer eligible tickers than `target_count` | Return only eligible tickers with equal weights. |
| No eligible tickers | No ticker passes eligibility | Return the selection-model instance's configured fallback ticker. |
| Data availability | Feature row is missing for a ticker/date | Exclude or mark unavailable; do not forward-fill unless explicitly configured. |
| Look-ahead guard | Ranking at date `D` | Use only data available before or at the allowed signal cutoff for `D`. |

## Metrics

| Metric | Meaning |
| --- | --- |
| `eligible_count` | Number of tickers passing filters. |
| `fallback_rate` | Percent of selection dates using fallback. |
| `selection_count` | Number of selected tickers per allocation cycle. |
| `forward_return_20d` | Forward 20-trading-day return of selected tickers. |
| `forward_return_60d` | Forward 60-trading-day return of selected tickers. |
| `excess_return_vs_universe` | Forward return versus equal-weight universe baseline. |
| `turnover_of_selected_names` | How often selected names change. |

## Pass Criteria

- Eligibility and ranking match the documented formulas.
- The fallback ticker is used only when no ticker is eligible.
- No future data is used in eligibility or ranking.
