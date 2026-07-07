# External Strategies

This directory is reserved for strategies defined by external authors.

Before evaluating an external strategy, record:

- strategy name
- author
- source URL or citation
- version
- publication date
- author backtest end date, if known
- download date
- exact frozen specification
- interpretation decisions for ambiguous rules
- configuration hash

Use the author's publication date or documented data cutoff to define honest
out-of-sample periods. Do not tune the strategy after seeing out-of-sample
results and still treat the same period as a clean test.

Recommended result labels:

| Label | Meaning |
| --- | --- |
| `REPLICATION` | Data may have influenced the original author or is used to verify implementation behavior. |
| `OUT_OF_SAMPLE` | Data after the author's documented data cutoff. |
| `POST_PUBLICATION` | Data after the strategy was publicly available. |

Warm-up data may be used to compute indicators before the evaluation start, but
it should not be included in reported performance metrics.
