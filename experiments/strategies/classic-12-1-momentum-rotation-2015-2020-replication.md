# Classic 12-1 Momentum Rotation 2015-2020 Replication

## Experiment ID

`classic-12-1-momentum-rotation-2015-2020-replication`

## Status

`preregistered`

## Hypothesis

The unchanged top-ten 12-1 monthly rotation will remain profitable after costs
and outperform SPY and the dated equal-weight eligible universe over 2015-2020,
without relying on one ticker or year for half of total profit.

## Reference Configuration

[TC-002: 2015-2020 Temporal Replication](../../backtests/strategies/classic-12-1-momentum-rotation/tc-002-point-in-time-sp500-2015-2020-replication.md)

## Declared Deltas

Only the [evaluation](../../stages/OPERATIONS.md#evaluation-plans) dates differ
from TC-001. VFMO is a separately labeled
common-history benchmark beginning in 2018. All strategy and
[execution](../../stages/OPERATIONS.md#execution-and-execution-models) rules
are unchanged.

## Success Criteria

1. Positive CAGR and terminal profit under 10 bps plus $1/order.
2. Gross and after-cost full-window terminal value exceed SPY.
3. Gross terminal value exceeds the dated equal-weight eligible universe.
4. Strategy return exceeds VFMO over their common 2018-2020 history.
5. Average candidate coverage is at least 95%, with all exclusions reported.
6. No ticker or calendar year supplies half of total profit.
7. Positive return occurs in more calendar years than negative return.
8. Maximum drawdown is no more than ten percentage points worse than SPY.

## Run Index

Pending.

## Results

Pending.

## Findings

Pending.

## Decision

Pending.
