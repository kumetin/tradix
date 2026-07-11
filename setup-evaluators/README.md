# Setup Evaluator

Setup evaluators define reusable stock setup evaluation rubrics for watchlist
reviews.

Default evaluator for "review the watchlist":

- `lower-risk-swing-entry.md` - lower-risk swing entry table with concrete
  trade construction.

The implementation source of truth for setup construction and scoring lives in:

- `scripts/setup-evaluators/lower_risk_swing_entry.py`
- `scripts/setup-evaluators/README.md`

When using a setup evaluator:

1. Read this README first.
2. Read the selected evaluator.
3. Use local daily price/features data where available.
4. Do not fabricate analyst targets, analyst counts, rating changes, estimate
   revisions, fundamentals, earnings quality, or institutional sponsorship
   signals. Use reliable current sources when available; otherwise mark the
   field `N/A` and lower confidence.
5. Treat the output as decision-support research, not certainty or personalized
   financial advice.
