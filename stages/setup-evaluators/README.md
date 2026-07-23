# [Setup Evaluator](../OPERATIONS.md#setup-evaluators)

Setup evaluators are reusable components that classify one instrument-date
setup, score its attractiveness and evidence, and may construct a trade plan.
Watchlist reviews are one consumer; configured strategies and isolated
component backtests may also use them.

Descriptors in this directory follow the
[setup-evaluator schema](../DESCRIPTOR-SCHEMA.md#setup-evaluator-schema).

## Active Evaluators

- [`lower-risk-swing-entry`](lower-risk-swing-entry.md) — lower-risk swing
  entry classification, scoring, and trade-plan construction.

Each descriptor owns the stable component contract. When executable, its linked
implementation owns formulas, thresholds, constants, and status-assignment
logic. Presentation formats belong to the consuming workflow rather than the
stage descriptor.

## Archive

Files under [`archive/`](archive/README.md) are inactive historical descriptors.
They are retained for provenance and must not be selected by new strategies,
experiments, or watchlist reviews.

## Consumer Rules

- Read the selected descriptor and invoke its implementation when present.
- Supply only point-in-time
  [market data](../OPERATIONS.md#market-data-resolution) and external evidence.
- Do not fabricate analyst, estimate, fundamental, event, or sponsorship data.
- Use the evaluator's emitted classification and scores; do not assign them
  manually.
- Keep reporting layout, chat phrasing, and artifact formatting in the caller.
