# Investable US Equities Top 1000

## ID

`investable-us-equities-top-1000`

## Stage Type

`universe-model`

## Purpose

Produce a broad, reproducible US common-stock candidate set using explicit
listing, instrument-type, investability, data-sufficiency, and float-market-cap
coverage rules.

## Input Contract

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `as_of` | trading date or timestamp | Yes | Date or time for which the population is resolved. |
| `knowledge_cutoff` | timestamp | Yes | Latest classification, market, and fundamental publication time observable by the run. |
| `security_population` | point-in-time instrument records | Yes | Stable IDs and effective-dated listing and classification fields. |
| `market_snapshots` | map of instrument ID to dated market history | Yes | Close, adjusted close, volume, and actual trading-row history. |
| `fundamental_snapshots` | map of instrument ID to effective-dated fundamentals | Yes | Point-in-time float shares used to calculate float market capitalization. |

## Output Contract

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `as_of` | trading date or timestamp | Yes | Coverage date echoed for traceability. |
| `knowledge_cutoff` | timestamp | Yes | Knowledge boundary used for resolution. |
| `candidates` | ordered instrument records | Yes | Included instruments with coverage rank, stable ID, and current symbol. |
| `decisions` | map of instrument ID to inclusion decision/reasons | Yes | Predicate results, exclusions, and coverage cutoff results. |
| `source_dates` | map of input family to effective/snapshot timestamps | Yes | Security-master, market, and fundamental vintages used. |

## Behavior

Start from active primary US listings with `asset_class = equity` and
`security_type = common_stock`. Exclude ADRs, ETFs, leveraged products, and
inverse products. On the latest trading row on or before `as_of`, require an
unadjusted close of at least USD 5, 20-day average dollar volume of at least USD
5 million, at least 200 valid actual trading rows in the trailing 252-session
window, and non-null adjusted close and volume. Calculate point-in-time
`float_market_cap = close * float_shares`, rank descending, retain 1,000, and
break ties by ascending `instrument_id`.

These rules express market coverage and practical investability. They do not
use momentum, valuation attractiveness, expected-return signals, or portfolio
target construction.

## Parameters

| name | type | required | default | constraints | description |
| --- | --- | --- | --- | --- | --- |
| `listing_country` | ISO country code | No | `US` | Fixed by descriptor. | Restricts the population to US primary listings. |
| `asset_class` | enum | No | `equity` | Fixed by descriptor. | Restricts the population to equity instruments. |
| `security_type` | enum | No | `common_stock` | Fixed by descriptor. | Excludes funds, preferred shares, warrants, and other instrument types. |
| `minimum_close_usd` | decimal | No | `5` | Fixed by descriptor; USD, non-negative. | Minimum unadjusted share price used as an investability floor. |
| `adv_window` | positive trading-day count | No | `20` | Fixed by descriptor. | Actual-row window used for average dollar volume. |
| `minimum_adv_usd` | decimal | No | `5000000` | Fixed by descriptor; USD, non-negative. | Minimum average daily dollar volume. |
| `history_window` | positive session count | No | `252` | Fixed by descriptor. | Session window used for data-sufficiency measurement. |
| `minimum_valid_rows` | positive integer | No | `200` | Fixed by descriptor; no greater than `history_window`. | Minimum actual nonblank market rows in the history window. |
| `coverage_field` | field name | No | `float_market_cap` | Fixed by descriptor. | Non-alpha size field used to define coverage. |
| `coverage_direction` | enum | No | `descending` | Fixed by descriptor. | Retains larger float-adjusted companies first. |
| `coverage_limit` | positive integer | No | `1000` | Fixed by descriptor. | Maximum candidate count. |
| `missing_data_policy` | enum | No | `exclude_and_report` | Fixed by descriptor. | Excludes unknown required values and records the reason. |
| `tie_breaker` | field name | No | `instrument_id` | Fixed by descriptor; unique and ascending. | Makes the coverage cutoff deterministic. |

## Data Requirements

An effective-dated security master, canonical daily prices, point-in-time float
shares, and derived `adv_dollar_20`, valid-row count, and float-market-cap fields
are required. The current local dataset lacks stable instrument IDs,
classifications, and point-in-time float shares, so this descriptor is not
executable until those canonical inputs are added.

## Point-in-Time Rules

Use the latest values effective at `as_of` and published or ingested no later
than `knowledge_cutoff`. Do not reconstruct historical float shares,
classifications, listing status, or delistings from current records. Use actual
market rows without forward-filling missing OHLCV values.

## Failure Behavior

Fail when a required input family is unavailable for the cutoff. Exclude and
report an individual instrument when a required predicate or coverage value is
unknown. Return fewer than 1,000 candidates when fewer qualify; never relax
thresholds, substitute current fundamentals, or add a portfolio fallback.

## Benchmark Contract

Replay identical dated security-master, market, and fundamental fixtures.
Measure classification correctness, investability pass rate, rank and cutoff
correctness, membership stability and turnover, coverage by float market
capitalization, missing-data exclusions, delisted-security handling, and
deterministic repeatability.

## Implementation

None. This descriptor defines the required contract before the canonical
security-master, fundamental, and universe-query engine are introduced.
