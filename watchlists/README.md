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
5. Use the [setup evaluators](../stages/OPERATIONS.md#setup-evaluators) under `stages/setup-evaluators/` to rank the list.
6. Follow the daily stock price data workflow in `AGENTS.md` for any price,
   moving-average, volume, volatility, return, RSI, support/resistance, or
   drawdown analysis.

## Review Output

For watchlists with more than 10 unique tickers:

1. Show only the top 10 ranked setups in the chat response.
2. Generate the complete one-row-per-ticker ranking as both Markdown and CSV
   artifacts under `artifacts/stock/watchlist-reviews/`.
3. Link both complete-result files from the chat response.
4. Include the three short evaluator notes: best setup now, best
   wait-for-pullback setup, and highest-risk name despite upside.

For watchlists with 10 or fewer unique tickers, return the complete ranking in
chat; separate result files are optional.
