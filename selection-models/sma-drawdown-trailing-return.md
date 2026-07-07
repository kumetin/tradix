# SMA Drawdown Trailing Return

Selects one target ticker from a configured universe using trend health,
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

Among eligible tickers, select the ticker with the highest trailing return over
the configured ranking window.

## Fallback

If no ticker is eligible, use the fallback ticker supplied by the universe
profile.

## Parameters

| Parameter | Description |
| --- | --- |
| `medium_sma_window` | Medium-term SMA window used in the eligibility rule. |
| `long_sma_window` | Long-term SMA window used in the eligibility rule. |
| `rolling_high_window` | Window used to compute drawdown from recent highs. |
| `max_drawdown` | Minimum allowed drawdown value. A ticker must be above this threshold. |
| `ranking_return_window` | Trailing return window used to rank eligible tickers. |
