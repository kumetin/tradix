# Setup Rankers

Setup rankers define reusable stock setup ranking rubrics for watchlist
reviews.

Default ranker for "review the watchlist":

- `lower-risk-swing-entry.md` - lower-risk swing entry table with concrete
  trade construction.

Use the other rankers when the request calls for them:

- `quantitative-swing-score.md` - quantitative swing-trade scorecard and
  conviction ranking.
- `qualitative-pullback-buy-zone.md` - lighter qualitative pullback and
  buy-zone check.

When using a ranker:

1. Read this README first.
2. Read the selected ranker.
3. Use local daily price/features data where available.
4. Do not fabricate analyst targets, analyst counts, rating changes, estimate
   revisions, fundamentals, earnings quality, or institutional sponsorship
   signals. Use reliable current sources when available; otherwise mark the
   field `N/A` and lower confidence.
5. Treat the output as decision-support research, not certainty or personalized
   financial advice.
