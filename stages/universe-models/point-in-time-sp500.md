# Point-in-Time S&P 500

## ID

`point-in-time-sp500`

## Stage Type

`universe-model`

## Purpose

Resolve the S&P 500 membership that was effective and knowable at a requested
decision cutoff, producing an unbiased dated candidate set rather than applying
today's constituents to historical decisions.

## Input Contract

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `as_of` | trading date or timestamp | Yes | Date or time for which membership is resolved. |
| `knowledge_cutoff` | timestamp | Yes | Latest membership publication time observable by the run. |
| `security_population` | point-in-time instrument records | Yes | Stable IDs, symbols, classifications, listing status, and effective dates. |
| `membership_records` | effective-dated membership records | Yes | S&P 500 additions, removals, effective intervals, and `known_at` timestamps. |
| `market_snapshots` | map of instrument ID to dated market rows | Yes | Confirms that required downstream adjusted-close and volume inputs exist. |

## Output Contract

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `as_of` | trading date or timestamp | Yes | Membership date echoed for traceability. |
| `knowledge_cutoff` | timestamp | Yes | Knowledge boundary used for resolution. |
| `candidates` | ordered instrument records | Yes | Effective S&P 500 members ordered by stable `instrument_id`. |
| `decisions` | map of instrument ID to inclusion decision/reasons | Yes | Membership, listing, and data-sufficiency results. |
| `source_dates` | map of input family to effective/snapshot timestamps | Yes | Membership and market-data vintages used. |

## Behavior

Select records where `membership_set_id = SP500`, `member_from <= as_of`,
`member_to` is absent or after `as_of`, and `known_at <= knowledge_cutoff`.
Require the instrument classification and primary listing to be effective at
`as_of`. Require non-null adjusted close and volume on the latest trading row on
or before `as_of`. Order included candidates by `instrument_id`.

This model reproduces an external membership mandate; it does not rank members
by expected return or emit portfolio targets.

## Parameters

| name | type | required | default | constraints | description |
| --- | --- | --- | --- | --- | --- |
| `membership_set_id` | string | No | `SP500` | Fixed by descriptor. | External membership series to resolve. |
| `require_active_primary_listing` | boolean | No | `true` | Fixed by descriptor. | Excludes inactive and non-primary listing records. |
| `required_market_fields` | list of field names | No | `adj_close, volume` | Fixed by descriptor. | Minimum downstream [market data](../OPERATIONS.md#market-data-resolution) required for inclusion. |
| `missing_data_policy` | enum | No | `exclude_and_report` | Fixed by descriptor. | Excludes a member with missing required data while preserving the reason. |
| `tie_breaker` | field name | No | `instrument_id` | Fixed by descriptor; unique and ascending. | Makes candidate ordering deterministic. |

## Data Requirements

An effective-dated security master, historical S&P 500 membership with
`member_from`, `member_to`, and `known_at`, and canonical daily market rows are
required. The current price dataset does not contain historical membership or
stable instrument IDs, so this descriptor is not executable until those
canonical datasets are added.

## Point-in-Time Rules

Use only classification and membership versions effective at `as_of` and known
by `knowledge_cutoff`. Later constituent corrections, later ticker mappings,
and current-constituent reconstruction are prohibited. Market rows must not be
later than `as_of`.

## Failure Behavior

Fail when the security master or membership series is unavailable for the
cutoff. Exclude and report individual members missing required market fields.
Return an empty candidate set only when the effective membership query genuinely
returns no rows; never substitute current membership or a portfolio fallback.

## Benchmark Contract

Replay dated security-master and membership fixtures. Compare output with a
trusted effective-date membership tape using constituent precision/recall,
addition/removal timing, current-constituent leakage count, missing-data
exclusions, membership turnover, and deterministic repeatability.

## Implementation

None. This descriptor defines the required contract before canonical historical
membership data and an executable query engine are introduced.
