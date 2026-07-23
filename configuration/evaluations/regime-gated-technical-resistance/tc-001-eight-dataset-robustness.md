# Regime-Gated Technical Resistance TC-001 Eight-Dataset Robustness

| Setting | Value |
| --- | --- |
| `warmup_start` | `1996-01-02` |
| `evaluation_start` | `1997-01-02` |
| `evaluation_end` | `2026-07-17` |
| `split_method` | Fixed regime windows plus five fixed static-universe replications |
| `pre1999_window` | `1997-01-02` to `1998-12-31` |
| `crisis_window` | `2007-01-03` to `2009-12-31` |
| `recovery_window` | `2010-01-04` to `2013-12-31` |
| `five_universe_window` | `2015-01-02` to `2026-07-17` |
| `holdout_status` | Iterative research; only pre-1999 was one-shot temporal evidence |

Warm-up observations initialize indicators and are excluded from reported
metrics. Every dataset is reported separately before aggregate statistics.
Current universe membership is projected backward, so no result is a clean
point-in-time S&P 500 test.
