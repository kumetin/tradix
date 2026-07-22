# [Setup Evaluator](../OPERATIONS.md#setup-evaluators) Implementation

This package contains the implementation source of truth for setup evaluators.

## Lower-Risk Swing Entry

Prompt wrapper:

```text
stages/setup-evaluators/lower-risk-swing-entry.md
```

Implementation:

```text
stages/setup-evaluators/lower_risk_swing_entry.py
```

Public flow:

```python
import importlib.util
import sys
from pathlib import Path

module_path = Path("stages/setup-evaluators/lower_risk_swing_entry.py")
spec = importlib.util.spec_from_file_location("lower_risk_swing_entry", module_path)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
LowerRiskSwingEntryEvaluator = module.LowerRiskSwingEntryEvaluator

setup = LowerRiskSwingEntryEvaluator.construct_setup(ticker, feature_rows)
scored = LowerRiskSwingEntryEvaluator.score_setups([setup])
```

Use `construct_setup(...)` before scoring. It derives support, resistance, buy
limit, trailing stop, initial invalidation, take-profit, reward/risk, and the
normalized evaluator inputs from point-in-time feature rows.

Use `score_setups(...)` for table output. It scores each constructed setup,
sorts by setup score, evidence score, and reward/risk, and returns setup fields
paired with the scored [evaluation](../OPERATIONS.md#evaluation-plans).

Use `evaluate(...)` only when the caller has already created
`LowerRiskSwingEntryInputs` using the same construction rules.

## Source of Truth Rule

Keep formulas, thresholds, constants, and component scoring rules in
`lower_risk_swing_entry.py`.

The markdown evaluator should document the human-facing output contract and the
component keys, but should not duplicate scoring formulas. This avoids drift
between prompt text and backtestable code.

## Output Components

The lower-risk swing-entry evaluator returns two independent 0-100 values:

- `setup_score`: setup attractiveness, used as `setup_score` in backtest outputs.
- `evidence_score`: data completeness and reliability, not a prediction that the trade will work.

`setup_score` is the sum of the setup-score breakdown fields:

```text
EP + SQ + RR + TS + AS + ER
```

| Key | Meaning | Max |
| --- | --- | --- |
| `SS` | Total setup score / setup attractiveness | `100` |
| `EP` | Entry proximity to intended buy limit | `25` |
| `SQ` | Support quality | `20` |
| `RR` | Reward/risk quality | `20` |
| `TS` | Trend structure | `15` |
| `AS` | Analyst support | `10` |
| `ER` | Extension risk | `10` |

`evidence_score` is the sum of the evidence-score breakdown fields:

```text
PD + SR + MA + AD + TM + RG
```

| Key | Meaning | Max |
| --- | --- | --- |
| `ES` | Total evidence score / data reliability | `100` |
| `PD` | Price data quality | `20` |
| `SR` | Support/resistance objectivity | `15` |
| `MA` | Moving-average and indicator completeness | `15` |
| `AD` | Analyst data completeness | `20` |
| `TM` | Trade-math consistency | `20` |
| `RG` | Recency or event-gap risk | `10` |

The exact thresholds are defined in the Python evaluator and its docstrings.
