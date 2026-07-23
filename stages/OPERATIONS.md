# Strategy Operations and Stage Responsibilities

This page is the canonical index for strategy operations, reusable stage types,
and run configuration. It explains what each concept owns, how reusable
behavior is benchmarked independently, and how a concrete implementation is
evaluated inside a configured strategy backtest.

Link the first meaningful mention of a named operation or stage type in each
Markdown document to the corresponding section here. Repeated mentions in the
same document do not all need links.

## Trigger

**Responsibility:** begin a decision cycle and establish its decision time and
knowledge cutoff. A trigger determines when evaluation occurs; it does not rank
opportunities or predict returns.

**Independent assessment:** triggers are configuration rather than performance
components. Validate calendar behavior, cutoff semantics, duplicate/missed
firings, holidays, and point-in-time safety with deterministic schedule tests.

**Configured-strategy assessment:** compare trigger frequencies or timing rules
as strategy-scenario variants while holding the thesis and other bindings
constant. Measure opportunity capture, turnover, latency, and resulting
performance without attributing predictive skill to the trigger alone.

## Universe Resolution and Universe Models

**Responsibility:** produce the dated instruments that may be considered. A
static universe supplies fixed input data; a universe model applies a measurable
point-in-time coverage or investability mandate. Neither emits portfolio
targets or expected-return ranks.

**Independent assessment:** benchmark a universe model on point-in-time
membership correctness, mandate coverage, investability, membership stability,
turnover, missing-data behavior, opportunity coverage, and deterministic
replay. Static ticker lists receive schema and availability validation only.

**Configured-strategy assessment:** vary the universe binding—either a static
universe configuration profile or a universe-model descriptor—in otherwise
identical strategy scenarios to test breadth, capacity, constituent bias, and
out-of-population robustness. Compare against equal-weight exposure to each
dated universe and avoid treating universe choice as selection-model alpha.

## Market-Data Resolution

**Responsibility:** supply normalized prices, features, fundamentals, calendars,
and other evidence that was knowable at the operation's cutoff. The service
owns data availability and provenance, not investment decisions.

**Independent assessment:** market-data providers are infrastructure rather
than performance components. Validate schemas, timestamps, revisions,
adjustments, missing rows, corporate actions, source agreement, and leakage
guards using fixed data fixtures and provider reconciliation.

**Configured-strategy assessment:** replay the same strategy with controlled
data-source or data-quality variants to quantify sensitivity to latency,
coverage, revisions, and missingness. Such comparisons diagnose robustness;
they do not turn the provider into a predictive stage.

## Selection and Selection Models

**Responsibility:** apply thesis-specific eligibility, score or rank candidates,
and emit ordered target/weight intent. A selection model owns which eligible
opportunities the strategy wants, before account-state transition or fills.

**Independent assessment:** use identical dated candidate and feature fixtures.
Measure rank correlation, rank-bucket monotonicity, top-selection excess forward
outcome, hit rate, fallback rate, deterministic stability, and behavior under
missing inputs. No complete portfolio simulation is required.

**Configured-strategy assessment:** bind the selection-model descriptor to a
fixed universe binding, portfolio-policy descriptor, execution-model
descriptor, funding profile, and evaluation plan. Compare descriptor or
parameter variants against simple selectors and equal-weight dated-universe
exposure, measuring whether isolated rank quality survives turnover, capacity,
cash, and costs.

## Setup Evaluators

**Responsibility:** classify one instrument-date setup, score its evidence, and
optionally construct entry, invalidation, and target levels. A setup evaluator
does not decide portfolio-wide target weights or account transitions.

**Independent assessment:** evaluate calibration, score monotonicity, forward
returns, adverse/favorable excursion, trade-plan reachability, evidence quality,
and missing-data behavior over identical ticker-date fixtures.

**Configured-strategy assessment:** use the evaluator as a gate or scoring input
inside otherwise fixed strategy backtests. Compare filtered versus unfiltered
signals and baselines while measuring opportunity loss, turnover, portfolio
effects, and whether standalone calibration survives the strategy context.

## Portfolio Transitions and Portfolio Policies

**Responsibility:** combine target intent with positions, settled/unsettled cash,
and constraints to produce order intents. Portfolio policy owns retention,
selling, accumulation, rotation, rebalancing, sizing, and deliberate cash.

**Independent assessment:** replay identical target-intent and account-state
tapes. Compare turnover, cash drag, concentration, tracking error, drawdown,
constraint adherence, retained-position decisions, and deterministic order
generation.

**Configured-strategy assessment:** vary policies around a fixed thesis and
selection tape to test whether predictive evidence survives alternative
portfolio expressions. Attribute turnover, concentration, tax, and cash effects
to policy rather than selection skill.

## Execution and Execution Models

**Responsibility:** convert order intents and market/account state into fills,
rejections, fees, slippage, settlement movements, and resulting positions. It
owns operational realism, never desired holdings or expected returns.

**Independent assessment:** replay identical order and market tapes. Measure
fill accuracy, implementation shortfall, costs, rejection and partial-fill
rates, settlement correctness, cash-ledger integrity, and deterministic replay.

**Configured-strategy assessment:** compare execution assumptions or broker
models with upstream intent fixed. Measure whether the thesis survives realistic
costs, latency, capacity, rejected orders, and settlement constraints.

## Funding Profiles

**Responsibility:** define exogenous cash contribution or withdrawal events.
Funding changes available capital but does not create a trading signal or a
desired portfolio transition.

**Independent assessment:** funding is run configuration, not an independently
benchmarkable performance component. Validate amounts, dates, currency,
non-negativity rules, and ledger application with deterministic fixtures.

**Configured-strategy assessment:** vary funding profiles to distinguish signal
quality from cash-flow timing and capital-path effects. Use time-weighted or
cash-flow-aware metrics as appropriate; do not attribute contribution-driven
growth to the strategy thesis.

## Evaluation Plans

**Responsibility:** define warm-up, train/validation/test partitions, rolling or
walk-forward schedules, locked holdouts, benchmarks, and reported metrics.
Evaluation observes a run and does not participate in trading decisions.

**Independent assessment:** evaluation plans are research configuration. Validate
date ordering, non-overlap, warm-up exclusion, holdout locks, benchmark
availability, and metric correctness with static and deterministic tests.

**Configured-strategy assessment:** apply the same declared plan across strategy
variants. Report full-period and partition-level results, preserve failed runs,
compare with SPY and equal-weight dated-universe baselines, and treat any rule
changed after a holdout result as no longer cleanly tested by that holdout.

## Choosing the Correct Test Layer

Use an isolated component benchmark only when the behavior has a stable direct
input/output contract and meaningful metrics without a complete strategy. Use a
configured strategy backtest when comparing a thesis implementation or when the
effect emerges only through interaction with other operations. Static inputs,
services, and run configuration receive correctness validation plus controlled
strategy sensitivity tests; correctness alone does not make them performance
components.
