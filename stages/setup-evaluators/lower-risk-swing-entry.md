# Lower-Risk Swing Entry

## ID

`lower-risk-swing-entry`

## Stage Type

`setup-evaluator`

## Purpose

Classify and rank one or more stock-date setups for lower-risk swing entry
quality. The evaluator favors constructive entries near support over extended
momentum entries and may construct entry, invalidation, stop, target, and
reward/risk levels. It does not select portfolio weights, create orders, or
format a watchlist report.

## Input Contract

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `as_of` | trading date | Yes | [Evaluation](../OPERATIONS.md#evaluation-plans) cutoff, represented by the latest accepted `feature_rows` date in the current Python API. |
| `ticker` | ticker ID | Yes | Instrument being evaluated. |
| `feature_rows` | ordered daily feature records | Yes | Point-in-time adjusted price, moving-average, indicator, and volume history through `as_of`. |
| `analyst_support` | evaluator classification | No | Point-in-time analyst-support classification supplied by the caller. Defaults to missing/weak. |
| `analyst_data_quality` | evaluator classification | No | Completeness of the supplied analyst evidence. Defaults to missing. |
| `recency_gap_risk` | evaluator classification | No | Known staleness or event-gap condition at `as_of`. Defaults to clean. |

Callers normally supply raw feature rows to `construct_setup(...)`. Direct
construction of normalized `LowerRiskSwingEntryInputs` is supported only when
the caller uses the same classifications as the implementation.

## Output Contract

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `as_of` | trading date | Yes | Latest accepted feature-row date, exposed as `latest_date`. |
| `ticker` | ticker ID | Yes | Normalized uppercase ticker. |
| `classification` | setup-status enum | Yes | Deterministic setup status. |
| `scores` | two bounded scores with named breakdowns | Yes | `setup_score` measures attractiveness; `evidence_score` measures data reliability. |
| `trade_plan` | structured levels or `None` fields | Yes | Current price, setup type, support, resistance, buy limit, trailing stop, invalidation, take profit, and reward/risk. |
| `reasons` | ordered reason-code strings | Yes | Status and component-score codes explaining the classification. |

The setup-score components are:

| Code | Meaning | Range |
| --- | --- | ---: |
| `EP` | Entry proximity | `0..25` |
| `SQ` | Support quality | `0..20` |
| `RR` | Reward/risk quality | `0..20` |
| `TS` | Trend structure | `0..15` |
| `AS` | Analyst support | `0..10` |
| `ER` | Extension risk | `0..10` |

The evidence-score components are:

| Code | Meaning | Range |
| --- | --- | ---: |
| `PD` | Price-data quality | `0..20` |
| `SR` | Support/resistance objectivity | `0..15` |
| `MA` | Indicator completeness | `0..15` |
| `AD` | Analyst-data completeness | `0..20` |
| `TM` | Trade-math consistency | `0..20` |
| `RG` | Recency or event-gap quality | `0..10` |

Status values are `Ready / near buy zone`, `Wait for pullback`,
`Watch breakout retest`, `Too extended`, `Weak analyst support`, and
`Avoid for now`. Their exact priority and thresholds are executable behavior,
not duplicated in this descriptor.

## Behavior

The evaluator deterministically:

1. removes rows without a usable adjusted close and orders the remaining rows
   by date;
2. derives constructive support, resistance, buy-limit, stop, invalidation,
   target, and reward/risk values;
3. normalizes market and optional external evidence into component
   classifications;
4. calculates setup-attractiveness and evidence-quality scores;
5. assigns one setup status and ordered reason codes; and
6. sorts batches by setup score, evidence score, and reward/risk, descending.

All formulas, thresholds, constants, status priority, and tie-breaking code live
only in the executable implementation.

## Parameters

The descriptor exposes the buy-limit and ready-status thresholds used by
component experiments. Risk-construction settings remain fixed:

| Name | Type | Required | Default | Constraints | Description |
| --- | --- | --- | --- | --- | --- |
| `buy_limit_offset` | decimal | No | `0` | `[0,1)` | Places near-support buy limits below support by this fraction; zero preserves the current-price baseline. |
| `entry_score_threshold` | integer | No | `18` | `0..25` | Minimum entry-proximity component required for `Ready / near buy zone`. |
| `atr_window` | integer trading days | No | `14` | Positive; fixed by descriptor | ATR lookback used in risk construction. |
| `initial_invalidation_atr_multiple` | decimal | No | `0.8` | Positive; fixed by descriptor | ATR buffer below support for initial invalidation. |
| `fallback_invalidation_pct` | decimal | No | `0.015` | `[0,1)`; fixed by descriptor | Support-relative invalidation buffer when ATR is unavailable. |
| `trailing_stop_atr_multiple` | decimal | No | `2.0` | Positive; fixed by descriptor | ATR multiple used for the trailing-stop distance. |
| `min_trailing_stop_pct` | decimal | No | `0.045` | `[0,1)`; fixed by descriptor | Lower bound on trailing-stop distance. |
| `max_trailing_stop_pct` | decimal | No | `0.12` | Greater than the minimum; fixed by descriptor | Upper bound on trailing-stop distance. |

Changing a fixed value requires changing the descriptor and implementation; an
experiment may override only the two declared runtime parameters.

## Data Requirements

- Daily adjusted OHLCV and derived feature rows through `as_of`.
- Sufficient actual observations for the moving averages, ATR, recent support,
  and trailing-high calculations used by the implementation.
- Optional analyst evidence with source timestamps when analyst support is
  supplied.
- No implicit forward-filling of blank or missing OHLCV rows.

## Point-in-Time Rules

- `feature_rows` must contain no row after `as_of`.
- Rolling levels and indicators use only accepted rows through the cutoff.
- External evidence must have been published and available by `as_of`.
- Future prices, later revisions, and future event outcomes are prohibited.
- A backtest must keep warm-up observations outside reported evaluation
  metrics.

## Failure Behavior

- No usable adjusted-close rows produce an empty setup with missing trade-plan
  levels rather than a fabricated price.
- Missing analyst evidence remains missing and lowers evidence quality; it is
  never inferred.
- Missing support, resistance, indicators, or trade math lowers the relevant
  component and may produce `Avoid for now`.
- Sorting remains deterministic when values are missing; missing reward/risk is
  ordered below numeric reward/risk.
- Invalid caller-supplied normalized classifications are programming errors and
  must not be coerced into favorable values.

## Benchmark Contract

Use identical ticker-date point-in-time fixtures and compare calibration,
score-bucket monotonicity, forward returns, maximum adverse/favorable
excursion, trade-plan reachability, missing-data behavior, and deterministic
ordering. The reusable protocol is
[`setup-evaluator-forward-outcome-benchmark`](../../backtests/components/setup-evaluators/setup-evaluator-forward-outcome-benchmark.md).

Full-strategy effects such as cash use, overlapping positions, turnover, and
[execution](../OPERATIONS.md#execution-and-execution-models) costs require a
configured strategy experiment and are not evidence of the evaluator's
isolated contract.

## Implementation

Source:
[`lower_risk_swing_entry.py`](lower_risk_swing_entry.py)

Public entry points:

```python
LowerRiskSwingEntryEvaluator.construct_setup(ticker, feature_rows, ...)
LowerRiskSwingEntryEvaluator.evaluate(normalized_inputs)
LowerRiskSwingEntryEvaluator.score_setups(constructed_setups)
```

Use `construct_setup(...)` before `score_setups(...)` for normal operation.
The Python module and its docstrings are the only source of formulas,
thresholds, constants, and status-assignment priority.
