# [Triggers](../../stages/OPERATIONS.md#trigger)

This directory contains reusable trigger configuration used by strategies,
backtests, paper-trading runners, and future live bots. A trigger is not a
reusable performance stage: it can be validated for correct firing, but its
economic value cannot be benchmarked without a strategy-specific definition of
opportunity.

Triggers can be time-driven, event-driven, condition-driven, or manual. A
calendar schedule is one kind of trigger, not the whole abstraction.

## Available Triggers

- [Monthly Allocation](monthly-allocation.md)
