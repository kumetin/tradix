# Setup Evaluator Implementation

This package contains the implementation source of truth for setup evaluators.

## Lower-Risk Swing Entry

Prompt wrapper:

```text
setup-evaluators/lower-risk-swing-entry.md
```

Implementation:

```text
scripts/setup-evaluators/lower_risk_swing_entry.py
```

Public flow:

```python
import importlib.util
import sys
from pathlib import Path

module_path = Path("scripts/setup-evaluators/lower_risk_swing_entry.py")
spec = importlib.util.spec_from_file_location("lower_risk_swing_entry", module_path)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
LowerRiskSwingEntryEvaluator = module.LowerRiskSwingEntryEvaluator

setup = LowerRiskSwingEntryEvaluator.construct_setup(ticker, feature_rows)
ranked = LowerRiskSwingEntryEvaluator.rank_setups([setup])
```

Use `construct_setup(...)` before scoring. It derives support, resistance, buy
limit, trailing stop, initial invalidation, take-profit, reward/risk, and the
normalized evaluator inputs from point-in-time feature rows.

Use `rank_setups(...)` for table output. It scores each constructed setup,
sorts by rank score, confidence, and reward/risk, and returns setup fields
paired with the ranked evaluation.

Use `evaluate(...)` only when the caller has already created
`LowerRiskSwingEntryInputs` using the same construction rules.

## Source of Truth Rule

Keep formulas, thresholds, constants, and component scoring rules in
`lower_risk_swing_entry.py`.

The markdown evaluator should document the human-facing output contract and the
component keys, but should not duplicate scoring formulas. This avoids drift
between prompt text and backtestable code.

## Output Components

Rank breakdown fields:

```text
RS, EP, SQ, RR, TS, AS, ER
```

Confidence breakdown fields:

```text
CS, PD, SR, MA, AD, TM, RG
```

The exact meanings and thresholds are defined in the Python evaluator and its
docstrings.
