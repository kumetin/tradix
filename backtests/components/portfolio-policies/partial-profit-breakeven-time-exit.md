# Partial Profit Breakeven Time Exit Benchmark

## Component Under Test

Component type: [`portfolio-policy`](../../../stages/portfolio-policies/README.md)

[Partial Profit Breakeven Time Exit](../../../stages/portfolio-policies/partial-profit-breakeven-time-exit.md)

## Question

On identical dated entry/bar tapes, does partial profit-taking followed by a
breakeven stop and opportunity-cost exit improve trade expectancy or downside
relative to simpler exit policies?

## Backtest Type

`isolated component backtest`

## Direct Input/Output Contract

Input is an immutable set of dated entry intents, next-session adjusted-open
entry references, completed adjusted daily bars, and per-lot session state.
Output is the policy's ordered exit intents and the resulting normalized
trade-level cash/quantity path. No new securities are selected.

## Variants

- full holding through the 378-session horizon;
- full liquidation at the 22.5% profit target;
- fixed 7.5% stop only;
- 50% partial profit plus breakeven stop without the 15-session stagnation exit;
- the complete partial-profit/breakeven/time-exit policy.

Every variant exits remaining quantity at the common maximum horizon.

## Outcome Model

Entries use next-session adjusted open. Resting stop and limit fills use the
descriptor's gap and ambiguous-bar rules. A close-triggered stagnation or
horizon market intent fills at the next valid adjusted open; no slippage, fees,
settlement, capital redeployment, or separate
[execution model](../../../stages/OPERATIONS.md#execution-and-execution-models)
is modeled. The breakeven replacement
becomes active on the session after a partial target fill.

## Metrics

- mean, median, annualized, and 5th-percentile trade return;
- positive-return rate, maximum adverse/favorable marked-to-market excursion;
- stop-gap loss, target, initial-stop, breakeven-stop, stagnation, and horizon rates;
- holding sessions and exit-leg turnover; and
- deterministic quantity/cash conservation error.

Portfolio CAGR, portfolio drawdown, and portfolio cash drag are outside this
isolated trade-path contract because entries may overlap and released cash is
not redeployed.

## Output Location

Store resolved configuration, normalized entry tape, trade outcomes, aggregate
summaries, and an execution report under:

```text
artifacts/stock/backtests/components/portfolio-policies/partial-profit-breakeven-time-exit/<run-directory>/
```
