# Top N SMA Drawdown Trailing Return

Selects multiple target tickers from a configured universe using trend health,
drawdown control, and trailing momentum.

## Eligibility Filter

A ticker is eligible if:

```text
(price > long_sma OR medium_sma > long_sma)
AND
drawdown from rolling high > max_drawdown
```

Where:

```text
drawdown = current adjusted close / highest adjusted close in rolling_high_window trading days - 1
```

## Ranking

Rank eligible tickers by trailing return over the configured ranking window.
Select the top `target_count` tickers.

## Target Weights

Use equal target weights across selected tickers:

```text
target_weight = 1 / number_of_selected_tickers
```

If fewer than `target_count` tickers are eligible, allocate equally across the
eligible tickers. If no ticker is eligible, allocate to the `fallback_ticker`
configured for this [selection](../OPERATIONS.md#selection-and-selection-models)-model instance.

## Parameters

| Parameter | Description |
| --- | --- |
| `target_count` | Maximum number of target tickers to hold. |
| `medium_sma_window` | Medium-term SMA window used in the eligibility rule. |
| `long_sma_window` | Long-term SMA window used in the eligibility rule. |
| `rolling_high_window` | Window used to compute drawdown from recent highs. |
| `max_drawdown` | Minimum allowed drawdown value. A ticker must be above this threshold. |
| `ranking_return_window` | Trailing return window used to rank eligible tickers. |
| `fallback_ticker` | Defensive target used when no candidate passes eligibility. |
