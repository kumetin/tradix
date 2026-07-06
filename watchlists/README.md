# Watchlists

Watchlists define ticker universes to review. They are not owned positions,
prior sells, or trade alerts unless the file explicitly says so.

Each watchlist may contain thematic section headings followed by
comma-separated ticker symbols. Preserve those headings as context when ranking
setups because the group can explain why a ticker is on the list.

When reviewing a watchlist:

1. Parse all ticker symbols from the selected file.
2. Preserve the source group/category for context.
3. Do not treat entries as alerts, prior sells, or portfolio holdings.
4. Evaluate entries as candidate setups unless the user says otherwise.
5. Use the setup rankers under `rankers/` to rank the list.
6. Follow the daily stock price data workflow in `AGENTS.md` for any price,
   moving-average, volume, volatility, return, RSI, support/resistance, or
   drawdown analysis.
