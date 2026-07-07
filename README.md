# Tradix

Tradix is a local research workspace for stock market data, feature
engineering, and strategy testing.

## What’s in here

- `data/stock/prices/daily/` - raw daily OHLCV price history by year
- `data/stock/features/daily/` - precomputed daily features derived from price
  history
- `scripts/market-data-fetchers/` - helpers for downloading market data
- `scripts/stock-data-enrichment/` - scripts for generating derived datasets
- `strategies/` - reusable strategy notes and rules
- `backtests/` - configured strategy instances that wire strategy parameters
  to reusable profiles
- `selection-models/` - reusable ticker selection rules
- `evaluations/` - data windows and train/validation/test split definitions
- `universes/` - reusable ticker universes and fallback selections
- `schedules/` - reusable calendar schedules
- `funding/` - reusable funding profiles
- `portfolio-policies/` - reusable portfolio behavior policies
- `execution-models/` - reusable execution and accounting assumptions
- `tests/` - component behavior tests and static profile validation specs
- `experiments/` - experiment registries and run metadata
- `external-strategies/` - provenance records for strategies defined elsewhere
- `watchlists/` - ticker universes to review for trade setups
- `rankers/` - reusable setup ranking rubrics for watchlist reviews

## Platform Model

Backtests are composed from reusable platform components:

```text
strategy
-> schedule
-> universe
-> selection model
-> entry rule
-> portfolio policy
-> execution model
-> funding profile
-> evaluation window
```

Keep generated output data under `data/stock/backtests/`. Keep reusable
definitions under their component directories.

## Research Guardrails

- Use point-in-time market access. A strategy or selection model must not see
  prices, features, constituents, analyst data, or fundamentals that were not
  known at the simulated decision time.
- Treat current-universe backtests as biased research tests unless the universe
  is reconstructed point-in-time. Label that limitation explicitly.
- Separate warm-up data from evaluation data. Warm-up rows may initialize
  indicators, but reported metrics start at the evaluation start date.
- Keep locked holdout results clean. Once a holdout period influences a rule or
  parameter choice, it is no longer an untouched test period.
- Record every meaningful experiment, not only the winner. Search history is
  part of how a result should be interpreted.
- Benchmark strategies against both `SPY` and an equal-weight version of the
  available universe when possible.
- For externally sourced strategies, freeze the exact rules and provenance
  before evaluating them. Use post-publication data as the cleanest evidence.

## Current Strategy

The active strategy being tested is documented here:

- [`strategies/momentum-rotation.md`](strategies/momentum-rotation.md)

It describes a monthly momentum rotation model with:

- monthly scheduled ranking
- a reusable selection model for trend/drawdown filtering and momentum ranking
- a high-beta universe supplied by a universe profile
- portfolio behavior supplied by reusable policy profiles
- a 4-down entry setup or month-end fallback

Configured backtests:

- [`TC-001: High-Beta Universe With SOXL`](backtests/momentum-rotation/tc-001-high-beta-with-soxl.md)
- [`TC-002: Random Universe`](backtests/momentum-rotation/tc-002-random-universe.md)
- [`TC-003: Random Universe Multi-Position Initial Only`](backtests/momentum-rotation/tc-003-random-universe-multi-position-initial-only.md)

## Component Tests

Component test specifications live under [`tests/`](tests/). Focus behavioral
tests on logic-heavy components:

- `selection-models/`
- `portfolio-policies/`
- `execution-models/`

Use static validation checks for mostly declarative profiles such as
`universes/`, `funding/`, schedules, evaluations, and backtest links.

## Data Notes

Before analyzing daily stock data or calculating indicators such as moving
averages, RSI, volatility, or returns, read:

- `data/stock/prices/daily/.notes`
- `data/stock/features/daily/.notes`

Those notes cover ticker-history gaps, class ticker naming, and blank OHLCV
rows.

## IBKR Flex Portfolio Analysis

If you are analyzing an Interactive Brokers Flex portfolio, use:

```sh
scripts/ibkr-flex-query.sh ACCOUNT_ID portfolio
```

Local configuration is expected in:

- `~/.ibkr/flex-queries.csv`
- `~/.ibkr/flex-tokens.csv`

See `AGENTS.md` for the workflow.

## Watchlist Reviews

Watchlists define ticker universes, while prompt files define the setup ranking
rubrics used to evaluate them. For example:

- [`watchlists/ai-infrastructure.md`](watchlists/ai-infrastructure.md)
- [`rankers/lower-risk-swing-entry.md`](rankers/lower-risk-swing-entry.md)

See `watchlists/README.md`, `rankers/README.md`, and `AGENTS.md` for the
review workflow.
