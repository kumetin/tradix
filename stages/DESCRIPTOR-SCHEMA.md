# Reusable Stage Descriptor Schema

This document defines how a reusable stage and each concrete stage descriptor
are specified. It is the canonical schema for files under `stages/`.

The schema describes behavior and configuration; it does not prescribe a
serialization format. Markdown descriptors are currently canonical. An
executable implementation may use dataclasses, typed dictionaries, JSON, or
another representation as long as it preserves this contract.

## Common Stage Descriptor

Every concrete stage descriptor must define the following fields, normally as
second-level Markdown sections.

| Field or section | Required | Meaning |
| --- | --- | --- |
| `id` | Yes | Stable kebab-case identifier, normally the descriptor filename. |
| `stage_type` | Yes | One registered stage type from `stages/README.md`. |
| `purpose` | Yes | The single responsibility and decision owned by the stage. |
| `input_contract` | Yes | Point-in-time values accepted by the stage, including required fields and types. |
| `output_contract` | Yes | Values emitted by the stage, including required fields and types. |
| `behavior` | Yes | Deterministic rules that map inputs and configuration to outputs. |
| `parameters` | Yes | Configuration accepted by this implementation. Use `None` when it has no configurable parameters. |
| `data_requirements` | Yes | Required history, features, calendars, account state, or external evidence. |
| `point_in_time_rules` | Yes | Knowledge cutoffs and explicit leakage restrictions. |
| `failure_behavior` | Yes | Missing-data, invalid-input, empty-result, and fallback behavior. |
| `benchmark_contract` | Yes | Fixtures, direct metrics, and baselines that can evaluate this stage without a complete strategy. |
| `implementation` | When executable | Source path and public entry point. |

Human-readable titles and explanatory examples may accompany these fields, but
they do not replace them.

## Parameter Definition

Every row in a descriptor's `Parameters` or `Settings` table must define:

| Column | Required | Meaning |
| --- | --- | --- |
| `name` | Yes | Stable snake-case parameter name. |
| `type` | Yes | Primitive or named structured type. |
| `required` | Yes | Whether a configured stage instance must supply the value. |
| `default` | Yes | Default value, or `None` when there is no default. |
| `constraints` | Yes | Allowed range, enum, units, and cross-field constraints. |
| `description` | Yes | Behavioral effect of changing the parameter. |

A descriptor may fix a value rather than expose it to a strategy. Fixed values
still use this table and set `required = false`, `default` to the fixed value,
and state `fixed by descriptor` in `constraints`.

Dates use ISO `YYYY-MM-DD`; timestamps use UTC ISO 8601; percentages and returns
use decimal numbers unless a field explicitly declares another unit; trading-day
windows use positive integers.

## Stage Instance Reference

A strategy or backtest instantiates a stage with this logical shape:

```text
stage_type: registered stage family
descriptor: repository-relative descriptor path
parameters: descriptor parameter overrides
```

An override may change only parameters declared by the descriptor. Changing the
input/output contract or behavior creates a new descriptor, not another
parameter value.

## [Universe Model](OPERATIONS.md#universe-resolution-and-universe-models) Schema

A universe model maps a point-in-time security population to a dated candidate
set under an explicit coverage or investability mandate. It answers which
instruments may be considered; it does not estimate which instruments are most
attractive to own. Expected-return signals, strategy-specific eligibility,
target counts, and target weights belong to a [selection model](OPERATIONS.md#selection-and-selection-models).

`as_of` and `knowledge_cutoff` are runtime inputs, not model parameters. Market,
fundamental, classification, and membership values may be used only when they
were knowable by `knowledge_cutoff` and effective at `as_of`.

### Input contract

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `as_of` | trading date or timestamp | Yes | Date or time for which membership is resolved. |
| `knowledge_cutoff` | timestamp | Yes | Latest publication or ingestion time the model may observe. |
| `security_population` | point-in-time instrument records | Yes | Stable instrument IDs and effective-dated identity, classification, listing, and status fields. |
| `membership_records` | effective-dated membership records | Conditional | External index, mandate, or provider membership used by the descriptor. |
| `market_snapshots` | map of instrument ID to dated market fields/history | Conditional | Point-in-time price, volume, capitalization, and derived investability fields used by the descriptor. |
| `fundamental_snapshots` | map of instrument ID to effective-dated fundamentals | Conditional | Point-in-time shares, float, or other non-alpha coverage fields used by the descriptor. |
| `tradability_records` | effective-dated broker or venue eligibility | Conditional | [Execution](OPERATIONS.md#execution-and-execution-models)-environment restrictions when tradability is part of the mandate. |

Stable `instrument_id` values are required for joins and outputs. Symbols are
display attributes because ticker symbols can change or be reused.

### Query field families

Universe descriptors may declare predicates, ordering, and limits over these
field families. An executable descriptor must name the concrete fields and
operators it uses.

| Family | Representative fields | Purpose |
| --- | --- | --- |
| Population | `asset_class`, `security_type`, `listing_country`, `issuer_country`, `exchange_mic`, `currency`, `is_primary_listing`, `is_adr`, `is_etf`, `is_leveraged`, `is_inverse` | Define the instrument class and geographic or listing coverage. |
| External membership | `membership_set_id`, `member_from`, `member_to` | Resolve an externally maintained mandate such as point-in-time index membership. |
| Listing status | `listing_date`, `delisting_date`, `status`, `valid_from`, `valid_to` | Require the instrument and its classification to be effective at `as_of`. |
| Investability | `close`, `dollar_volume`, `adv_dollar_20`, `adv_dollar_63`, `market_cap`, `float_market_cap` | Apply fixed, non-alpha tradability or capacity floors. |
| Coverage | an approved population, membership, capitalization, or liquidity field plus `direction`, `limit`, and `tie_breakers` | Retain a reproducible portion of an eligible population. |
| Data sufficiency | `history_start`, `valid_bar_count`, `trading_days_252`, required-field null checks | Ensure downstream stages can be invoked without treating missing data as zero. |
| Point-in-time availability | `known_at`, provider publication time, ingestion time | Prevent information unavailable at the decision cutoff from entering membership. |

Fields such as trailing return, moving-average relationships, drawdown, RSI,
valuation attractiveness, earnings growth, analyst revisions, and volume
acceleration normally belong to selection models because they express relative
investment attractiveness. A fixed minimum price or average-dollar-volume
floor may belong to a universe model when it expresses investability rather
than expected performance.

### Configuration

Universe descriptors declare only the query behavior needed by their mandate:

| Configuration area | Required behavior |
| --- | --- |
| Population predicates | Exact fields, operators, values, and inclusion/exclusion semantics. |
| Membership predicates | Membership-set identity and effective-date rules when external membership is used. |
| Listing predicates | Active-listing and primary-listing rules. |
| Investability predicates | Fixed thresholds, units, lookback definitions, and aggregation methods. |
| Coverage rule | Optional ordering field, direction, limit, and deterministic tie-breakers. |
| Data-sufficiency rule | Required fields and minimum actual observations; missing rows are not forward-filled implicitly. |
| Missing-data policy | Exclude, fail, or explicitly report unknown values for every field family used. |
| Refresh rule | When membership is recomputed; this does not replace the runtime `as_of` input. |

The descriptor must be translatable into predicates and deterministic ordering over
the declared point-in-time inputs. Free-form concepts such as `large cap`,
`liquid`, or `US stock` are invalid unless reduced to concrete fields,
operators, thresholds, and classification values.

### Output contract

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `as_of` | trading date or timestamp | Yes | Input cutoff echoed for traceability. |
| `knowledge_cutoff` | timestamp | Yes | Knowledge boundary used to resolve the output. |
| `candidates` | ordered instrument records | Yes | Stable instrument IDs, current symbols, and any declared membership rank. |
| `decisions` | map of instrument ID to inclusion decision/reasons | Yes | Predicate results and deterministic exclusion reasons. |
| `source_dates` | map of input family to effective/snapshot timestamps | Yes | Data vintages used to produce the candidate set. |

An empty candidate set follows the descriptor's declared failure behavior; a
universe model does not select a defensive asset or portfolio target as an
implicit fallback.

Independent benchmarks compare mandate coverage, point-in-time correctness,
investability, membership stability and turnover, opportunity coverage,
missing-data behavior, and deterministic output over identical dated security
populations. They do not evaluate expected-return rank quality.

## Selection Model Schema

### Input contract

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `as_of` | trading date or timestamp | Yes | Decision cutoff. |
| `candidates` | ordered set of ticker IDs | Yes | Point-in-time candidate population. |
| `features` | map of ticker to feature row/history | Yes | Only values knowable by `as_of`. |
| `fallback_ticker` | ticker ID or `None` | Conditional | External fallback input when the descriptor supports fallback selection. |

### Configuration

Selection descriptors declare their eligibility parameters, ranking parameters,
target-count rule, weight rule, tie-breaking rule, and fallback mode. Common
parameter types include positive trading-day windows, decimal thresholds, and a
positive `target_count`.

### Output contract

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `as_of` | trading date or timestamp | Yes | Input cutoff echoed for traceability. |
| `eligibility` | map of ticker to decision/reasons | Yes | Candidate-level eligibility result. |
| `ranking` | ordered scored candidates | Yes | Deterministically ordered eligible candidates. |
| `targets` | ordered ticker/weight pairs | Yes | Portfolio intent before [portfolio policy](OPERATIONS.md#portfolio-transitions-and-portfolio-policies). May be empty only when declared. |
| `fallback_used` | boolean | Yes | Whether normal selection produced no targets. |

Independent benchmarks use rank correlation, rank-bucket monotonicity,
top-selection excess forward outcome, hit rate, fallback rate, and output
stability over identical dated candidate fixtures.

## [Setup Evaluator](OPERATIONS.md#setup-evaluators) Schema

### Input contract

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `as_of` | trading date or timestamp | Yes | [Evaluation](OPERATIONS.md#evaluation-plans) cutoff. |
| `ticker` | ticker ID | Yes | Instrument being evaluated. |
| `feature_rows` | point-in-time feature history | Yes | Price-derived evidence available at the cutoff. |
| `external_evidence` | structured values with source timestamps | Conditional | Analyst, fundamental, event, or sponsorship evidence used by the descriptor. |

### Configuration

Evaluator descriptors declare setup construction rules, score components and
ranges, evidence-quality treatment, status labels and priority, trade-plan
construction, missing-data policy, and deterministic sort/tie-breaking rules.
Thresholds must live in the executable implementation when one exists; the
descriptor identifies their names and behavioral meaning.

### Output contract

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `as_of` | trading date or timestamp | Yes | Input cutoff echoed for traceability. |
| `ticker` | ticker ID | Yes | Evaluated instrument. |
| `classification` | descriptor-defined enum | Yes | Setup status or action. |
| `scores` | named bounded numeric components | Yes | Attractiveness and evidence values with breakdowns. |
| `trade_plan` | structured levels or `None` | Yes | Entry, invalidation/stop, target, and reward/risk when constructible. |
| `reasons` | ordered reason codes/text | Yes | Evidence supporting the classification. |

Independent benchmarks use calibration, score monotonicity, forward outcomes,
adverse/favorable excursion, trade-plan reachability, and missing-data behavior
over identical ticker-date fixtures.

## Portfolio Policy Schema

### Input contract

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `as_of` | trading date or timestamp | Yes | Transition decision time. |
| `selection_intent` | ordered target ticker/weight pairs | Yes | Upstream desired exposure. |
| `portfolio_state` | positions, cost basis, and restrictions | Yes | Holdings before the transition. |
| `cash_state` | settled and unsettled cash ledger | Yes | Cash available under account rules. |

### Configuration

Portfolio-policy descriptors declare selling permission, supported target shape,
rebalance/rotation rule, position-retention rule, cash-use rule, sizing rule,
constraint handling, and behavior for empty or unchanged selection intent.

### Output contract

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `as_of` | trading date or timestamp | Yes | Input cutoff echoed for traceability. |
| `orders` | ordered order intents | Yes | Requested buys, sells, or no-op before execution modeling. |
| `retained_positions` | ticker IDs with reasons | Yes | Positions deliberately left unchanged. |
| `unallocated_cash` | amount with reason | Yes | Cash intentionally not assigned. |
| `constraint_events` | ordered events | Yes | Policy limits that changed the desired transition. |

Independent benchmarks replay identical target-intent/account-state tapes and
compare turnover, cash drag, concentration, tracking error, drawdown, and
constraint adherence.

## Execution Model Schema

### Input contract

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `submitted_at` | timestamp | Yes | Order submission time. |
| `orders` | ordered order intents | Yes | Requested trades from portfolio policy. |
| `market_tape` | point-in-time quotes/bars | Yes | Prices and liquidity visible to the model. |
| `calendar` | trading and settlement calendar | Yes | Sessions, holidays, and settlement dates. |
| `account_state` | positions and cash ledger | Yes | Pre-execution broker/account state. |

### Configuration

Execution descriptors declare supported order types, price/fill rule,
fractional-share rule, fees, taxes, slippage, partial-fill/rejection behavior,
settlement lag, currency/FX handling, and whether unsettled proceeds may be
reused. A numeric zero is a valid fixed model, not an omitted setting.

### Output contract

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `fills` | ordered fills | Yes | Quantity, price, cost, and timestamp per fill. |
| `rejections` | ordered rejection/partial-fill reasons | Yes | Unfilled order outcomes. |
| `cash_ledger` | dated settled/unsettled movements | Yes | Post-trade accounting result. |
| `positions` | resulting position state | Yes | Holdings after fills. |
| `costs` | fee, tax, slippage, and FX breakdown | Yes | Attributable execution costs. |

Independent benchmarks replay identical order/market tapes and compare fill
accuracy, implementation shortfall, costs, rejection rate, and settlement-ledger
correctness.
