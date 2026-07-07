# Alerts

This directory contains tracked alerts organized by purpose and strategy:

- **cut-loss-re-entry-watch.md** - Stocks sold at a loss that we monitor for re-entry opportunities
- **soxl-playbook-watch.md** - High-conviction alerts requiring fast response to intraday price movements

## Alert Review Process

When reviewing any alert, analyze using:
- Current price and recent price action
- Support and resistance levels
- Relationship to short-term and long-term moving averages
- Volume trends (short-term and long-term)
- Recent momentum and returns
- Time since initial trigger event

Provide practical re-entry or holding guidance based on available market data.

## "check alerts" command behavior

When you ask the assistant to `check alerts`, it will read the files in this
directory, extract configured alerts from every non-README file even if a
specific alert file is mentioned or linked, check trigger conditions against
live real-time market data, and return a concise, two-section summary. Use
local daily price and feature data only as supporting context for moving
averages, volume trends, and historical setup quality; do not use stale local
daily closes as the trigger source when live data is available.

- "Triggered Alerts:" — group entries by source alert filename as a subtitle,
  then list one-line entries for alerts whose trigger conditions are currently
  satisfied.
- "Non Triggered Alerts:" — group entries by source alert filename as a
  subtitle, then list one-line entries for each configured alert that is not
  currently triggered. Do not repeat the source filename on every alert row.

For re-entry watch files, treat the file's `Re-Entry Criteria` section as the
trigger framework. Classify a watched stock as triggered only when the criteria
are materially satisfied; otherwise summarize which criteria are partial or
missing. Do not say there is no trigger merely because there is no single
explicit price threshold.

The assistant will not produce long-form analysis in that response unless you
ask for it.
