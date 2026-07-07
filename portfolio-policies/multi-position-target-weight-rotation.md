# Multi Position Target Weight Rotation

The portfolio holds multiple selected tickers at target weights supplied by the
selection model.

## Allocation Intent

This policy expects a selection model that returns one or more target tickers
with target weights. For example:

```text
ABT 25%
AMGN 25%
SMCI 25%
WYNN 25%
```

## Sell Trigger

At each scheduled allocation cycle:

1. Sell positions that are not in the new target set.
2. Reduce positions that are above their target weight when rebalancing is
   required.
3. Keep positions that remain in the target set and are not above target.

## Buy Trigger

Buy or add to target positions that are below their target weight, using settled
cash according to the execution model.

If the execution model does not allow unsettled sale proceeds to be reused, the
portfolio may temporarily hold cash between the sell step and replacement buys.

## Rebalance Rule

Rebalance at each scheduled allocation cycle toward the target weights supplied
by the selection model.

## Settings

| Setting | Value |
| --- | --- |
| `allow_selling` | `true` |
| `position_policy` | Multiple target-weight positions |
| `rebalance_frequency` | Use schedule profile |
