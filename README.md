# Tradix

Tradix is a local research workspace for market-data collection, feature
engineering, reusable trading-strategy components, and backtesting.

This guide follows the order in which a new user normally uses the repository:
set up the code, create or restore the local dataset, define research
components, configure a strategy or component backtest, run it, and preserve
the results.

## 1. Prerequisites

The repository currently uses Python's standard library and shell scripts; it
does not have a package-install step. Use:

- Git
- Python 3.7 or newer
- network access when building data from public market-data providers
- rclone only when restoring or synchronizing data with Backblaze B2
- systemd and `flock` only when enabling the optional automatic B2 mirror

Clone the repository and enter it:

```sh
git clone YOUR_TRADIX_REPOSITORY_URL
cd Tradix
```

Run the data-independent code checks first:

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
```

Run static profile validation after creating or restoring the dataset in the
next step. Some validations intentionally confirm that universe tickers exist
in the local canonical data, so they are expected to fail in an empty clone.

`data/` and `artifacts/` are intentionally not stored in Git. A fresh clone
therefore starts without the canonical market dataset or previous run outputs.
Choose one of the two data-bootstrap paths below.

## 2. Create the Initial Local Dataset

The canonical local datasets are:

```text
data/stock/prices/daily/<year>/<ticker>.csv
data/stock/features/daily/<year>/<ticker>.csv
data/stock/analysts/activity/<year>/<ticker>.csv
```

Their `.notes` files live beside the CSVs and are part of the corresponding
dataset. Always read the applicable notes before analyzing the data; they
describe schemas, incomplete ticker histories, missing trading-day rows, class
ticker names, and known blank OHLCV rows.

You can either build a new dataset from web providers or restore an existing
snapshot from B2. You do not need B2 to use Tradix.

### Option A: Build a Dataset from Web Providers

Decide which tickers and dates the research needs. A strategy backtest normally
gets its tickers from the universe profile linked by its specification. The
currently executable isolated setup-evaluator backtest gets them from its
`--tickers` arguments.

Fetch those tickers into the canonical daily-price dataset. Repeat `--symbol`
for each ticker:

```sh
python3 scripts/market-data-fetchers/backfill_daily_stock_prices.py \
  2024-01-01 2026-07-21 \
  --symbol SPY \
  --symbol NVDA
```

The backfill fetcher tries Yahoo Finance first and has a Twelve Data fallback
for supported intervals. It merges rows by date and writes them into yearly
canonical CSVs. Existing rows are preserved and updated safely. If no symbols
are supplied, it updates every symbol already present in the local dataset.

Next, generate the derived daily features used for moving averages, trailing
returns, rolling highs, drawdowns, and volume features:

```sh
python3 scripts/stock-data-enrichment/precompute_daily_stock_features.py \
  --symbol SPY \
  --symbol NVDA
```

Analyst activity is optional. Fetch it only when the research uses analyst
ratings or price targets:

```sh
python3 scripts/market-data-fetchers/fill_analyst_activity.py \
  --start-date 2024-01-01 \
  --end-date 2026-07-21 \
  --symbol NVDA
```

More provider, interval, schema, and watchlist options are documented in
[`scripts/market-data-fetchers/README.md`](scripts/market-data-fetchers/README.md)
and feature-generation behavior in
[`scripts/stock-data-enrichment/README.md`](scripts/stock-data-enrichment/README.md).

Current limitation: the backtest driver does not yet inspect a backtest,
automatically fetch every missing ticker, and then generate its features.
Prepare the required local data with the commands above before running the
backtest. This explicit step is also what makes API use and changes to the
canonical dataset visible.

### Option B: Restore a Ready Dataset from Backblaze B2

Install rclone and create a Backblaze B2 remote. The repository defaults expect
a remote named `b2`, bucket `tradix-kumetix`, and file-name prefix `tradix/`.
For a different B2 snapshot, copy `.b2.env.example` to `.b2.env` and edit the
non-secret remote, bucket, and prefix values.

```sh
rclone config
scripts/setup-b2-sync.sh
```

Give the B2 application key read and write access only to the intended bucket
and prefix. Credentials belong in rclone's per-user configuration, never in
`.b2.env` or Git.

The setup script verifies that the remote is nonempty, downloads `data/` and
`artifacts/`, verifies them, records the canonical-row inventory, and marks the
clone as initialized. On a Linux system with user systemd, it also enables a
15-minute synchronization timer.

Use this instead when the clone should receive the snapshot but must not become
an automatically mirroring computer:

```sh
scripts/setup-b2-sync.sh --no-timer
```

Only one computer should have the authoritative timer enabled at a time. An
initialized authoritative clone mirrors its local `data/` and `artifacts/` to
B2, including artifact deletions. Before mirroring, it detects deleted
canonical rows, refetches missing price or analyst data, regenerates affected
features, and aborts without changing B2 if repair is incomplete. Initialization
checks, a nonempty-remote check, and a maximum deletion limit protect a fresh or
damaged clone from wiping the bucket.

Verify the restored snapshot:

```sh
scripts/b2-storage.sh verify
```

Whichever bootstrap path you chose, finish by checking that the repository
profiles and the now-present local dataset agree:

```sh
python3 tests/validation/validate_static_profiles.py
```

## 3. Understand the Research Model

Tradix composes a strategy from reusable stages:

```text
strategy
-> trigger
-> universe
-> selection model
-> entry rule
-> portfolio policy
-> execution model
-> funding profile
-> evaluation window
```

Each profile should own one kind of decision:

- `universes/` defines the eligible ticker set.
- `triggers/` defines when a strategy evaluates or allocates.
- `selection-models/` owns eligibility, ranking, target count, weights, and
  fallback selection.
- `portfolio-policies/` defines how holdings transition toward that selection.
- `execution-models/` defines fills, settlement, fees, slippage, and fractional
  shares.
- `funding-profiles/` defines capital contributions.
- `evaluations/` defines research windows and train/validation/test splits.
- `setup-evaluators/` defines reusable setup-scoring rubrics.

Read the `README.md` in a component directory before adding a profile there.
Keep data windows out of strategy parameters, and reference a reusable profile
instead of copying its values into each backtest.

Research must remain point-in-time: a simulated decision cannot see future
prices, features, constituents, analyst data, or fundamentals. Keep warm-up
rows outside reported performance, label current-universe bias, preserve locked
holdouts, and compare results with `SPY` and an equal-weight universe benchmark
when possible.

## 4. Write a Strategy and Its Components

Add or reuse the necessary component profiles first. Then create the strategy
definition and canonical ordered flow under `strategies/`:

```text
strategies/<strategy-name>.md
strategies/<strategy-name>.flow.md
```

The strategy definition explains the trading rules, data requirements,
portfolio behavior, and strategy parameters. The flow links the ordered
components used by backtests and, eventually, paper or live runners. See
[`strategies/README.md`](strategies/README.md) and the existing
[`momentum-rotation strategy`](strategies/momentum-rotation.md) for examples.

If the strategy came from an external source, freeze its exact rules and
provenance under `external-strategies/` before testing it. Post-publication data
is the cleanest out-of-sample evidence.

Run static validation after changing profiles or links:

```sh
python3 tests/validation/validate_static_profiles.py
```

## 5. Configure a Backtest

Put complete strategy backtest specifications under:

```text
backtests/strategies/<strategy-id>/<test-id>.md
```

A strategy backtest selects the strategy and flow, links concrete component
profiles, defines the evaluation and benchmarks, and states the edge being
tested.

Put tests of one reusable component under:

```text
backtests/components/<component-type>/<backtest-id>.md
```

Use an isolated component backtest for a component with a direct executable
input/output contract. Use a harnessed component backtest when the component
must be evaluated inside a fixed strategy pipeline. See
[`backtests/README.md`](backtests/README.md) for specification layout and
[`scripts/backtests/README.md`](scripts/backtests/README.md) for driver support.

Validate a specification without executing it:

```sh
python3 scripts/backtests/run_backtest.py \
  backtests/strategies/momentum-rotation/tc-001-high-beta-with-soxl.md \
  --validate-only
```

## 6. Run Tests and Backtests

Run the complete test suite before an experiment:

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
python3 tests/validation/validate_static_profiles.py
```

The current executable driver supports isolated setup-evaluator backtests. For
example:

```sh
python3 scripts/backtests/run_backtest.py \
  backtests/components/setup-evaluators/setup-signal-backtest.md \
  --evaluator lower-risk-swing-entry \
  -- \
  --tickers NVDA TLN ECL NEE SO AMZN XEL EXC \
  --start-date 2026-01-01 \
  --end-date 2026-03-31 \
  --frequency weekly \
  --horizons 5 10 \
  --min-setup-score 80 \
  --min-evidence-score 70 \
  --stop-model current \
  --scenario-slug utility-megacap-smoke
```

Strategy backtests and harnessed component backtests can currently be resolved
and validated, but no portfolio-level simulation engine is registered for
executing them yet.

Generated reports, CSVs, charts, logs, and visualizations belong under
`artifacts/stock/backtests/`; they are outputs, not input datasets. Record
meaningful runs, including unsuccessful ones, under `experiments/` once they
become part of the research record.

## 7. Maintain Data and B2 After Setup

Without B2, update canonical price data and regenerate features whenever a
research window or universe expands. Never treat a CSV fetched only to stdout
or a temporary directory as part of the dataset.

On an initialized authoritative B2 clone, reconcile or verify manually with:

```sh
scripts/b2-storage.sh reconcile
scripts/b2-storage.sh verify
```

Preview a transfer with `--dry-run`, list stored objects with
`scripts/b2-storage.sh list`, and inspect the automatic mirror with:

```sh
systemctl --user status tradix-b2-sync.timer
journalctl --user -u tradix-b2-sync.service
```

To move authority to another computer, first stop the old timer and perform a
final reconciliation. Then bootstrap the new clone and leave its timer as the
only enabled one:

```sh
systemctl --user disable --now tradix-b2-sync.timer
scripts/b2-storage.sh reconcile
```

## 8. Other Workflows

- `watchlists/` contains ticker lists for setup reviews; start with
  [`watchlists/README.md`](watchlists/README.md).
- `alerts/` contains sold-stock re-entry watches and alerts; start with
  [`alerts/README.md`](alerts/README.md).
- `tradingview/` contains Pine Script indicators.
- Interactive Brokers Flex portfolio analysis uses
  `scripts/ibkr-flex-query.sh ACCOUNT_ID portfolio` with private configuration
  under `~/.ibkr/`; see `AGENTS.md` for the protected-token workflow.

## Repository Map

```text
data/                       canonical and derived input datasets (not in Git)
artifacts/                  generated research outputs (not in Git)
scripts/market-data-fetchers/  market-data download and canonical merge tools
scripts/stock-data-enrichment/ derived-feature generation
scripts/backtests/          backtest validation and executable drivers
strategies/                 reusable strategy definitions and ordered flows
backtests/                  strategy and component backtest specifications
universes/                  reusable ticker universes
triggers/                   reusable strategy triggers
selection-models/           eligibility, ranking, targets, and fallback rules
portfolio-policies/         holdings-transition rules
execution-models/           fills, settlement, costs, and accounting assumptions
funding-profiles/            contribution schedules
evaluations/                evaluation windows and validation plans
setup-evaluators/           setup-scoring definitions
tests/                      executable tests and static validation
experiments/                experiment registries and run metadata
external-strategies/        frozen external specifications and provenance
watchlists/                 setup-review ticker lists
alerts/                     alert and re-entry-watch definitions
tradingview/                Pine Script indicators
```
