# Regime-Gated Classic 12-1 Momentum

## Thesis

Intermediate-term winners can continue outperforming, but momentum crashes
cluster around broad market downtrends and recoveries. Restricting new and
continued equity exposure to months when SPY closes at or above its 200-day
SMA should preserve much of the cross-sectional continuation premium while
reducing severe drawdowns and time underwater.

## Proposed Market Mechanism

The 12-1 signal captures slow information diffusion and institutional
position-building. The broad-market trend condition proxies environments in
which continuation is less exposed to forced deleveraging, correlation spikes,
and violent leadership reversals. Cash below the gate is risk control, not an
independent return forecast.

## Observable Point-in-Time Proxies

| Concept | Proxy |
| --- | --- |
| Intermediate stock momentum | Adjusted-close return from session 252 through session 21 before cutoff. |
| Relative leadership | Cross-sectional descending rank within dated membership. |
| Broad supportive regime | Completed SPY adjusted close at or above completed SMA200. |
| Defensive regime | Empty target intent, held as settled cash. |

## Prediction Horizon

Stock continuation is expected over three to twelve months. The regime is
reassessed monthly and may interrupt that holding horizon when the broad trend
turns negative.

## Required Strategy Behavior

Resolve point-in-time S&P 500 membership, calculate classic 12-1 momentum, and
hold ten equal-weight leaders only when SPY is at or above SMA200. When below,
rotate fully to cash. Use last-completed-session signals, next-session fills,
and T+1 sale-proceeds settlement.

Compatible components:

- [Classic 12-1 Momentum SPY SMA200 Gated](../stages/selection-models/classic-12-1-momentum-spy-sma200-gated.md)
- [Multi Position Target Weight Rotation](../stages/portfolio-policies/multi-position-target-weight-rotation.md)
- [IBKR Cash T+1](../stages/execution-models/ibkr-cash-t-plus-one.md)

## Strategy Parameters

None. The 252/21 stock signal, top-ten expression, monthly cadence, and
200-session market gate are frozen.

## Thesis-Preserving Variations

- distinct point-in-time broad U.S. universes;
- explicit realistic cost schedules;
- independent market periods; and
- fractional versus whole-share execution.

## Thesis-Changing Substitutions

- tuning the market SMA;
- using an individual-stock trend gate;
- adding volatility targeting, stops, fundamentals, sector caps, or short
  exposure;
- changing momentum lookback/skip or target count; or
- using a daily rather than monthly gate.

## Falsification Criteria

Reject or materially weaken the thesis when the frozen gate:

- fails to improve maximum drawdown by at least five percentage points versus
  ungated classic 12-1;
- fails to beat both SPY and VFMO after declared costs;
- reduces after-cost CAGR to less than three percentage points above the
  stronger of SPY and VFMO;
- produces non-positive mean rolling 12-month excess return versus either
  benchmark;
- depends on one ticker or calendar period for half of profit;
- has average candidate coverage below 95%; or
- fails a later genuinely untouched period or different point-in-time market.

## Pipeline Placement

The market gate, stock eligibility, ranking, target count, weights, and cash
intent belong to [selection](../stages/OPERATIONS.md#selection-and-selection-models).
Monthly timing is [trigger](../stages/OPERATIONS.md#trigger) configuration.
Rotation belongs to [portfolio policy](../stages/OPERATIONS.md#portfolio-transitions-and-portfolio-policies);
fills, costs, and T+1 settlement belong to
[execution](../stages/OPERATIONS.md#execution-and-execution-models).

## Backtests

- [TC-001: Point-in-Time S&P 500 Top-10 Monthly Regime Gate](../backtests/strategies/regime-gated-classic-12-1-momentum/tc-001-point-in-time-sp500-top-10.md)

## Data Requirements

Point-in-time membership, adjusted daily stock and SPY history, valid 12-1
endpoints, SPY SMA200, and explicit missing-history decisions.
