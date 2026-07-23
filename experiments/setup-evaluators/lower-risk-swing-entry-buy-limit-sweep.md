# Lower-Risk Swing Entry Buy-Limit Sweep

## Experiment ID

`lower-risk-swing-entry-buy-limit-sweep`

## Status

`rejected_for_promotion`

## Hypothesis

The 65-80% stop-loss rate from the previous stop-model sweep is not caused by stop width, but by **entry placement too close to support**. Requiring deeper pullbacks below support (1-2%) will provide margin of safety, reduce whipsaw risk, and improve win rates and average returns.

## Reference Configuration

- [Setup evaluator](../../stages/OPERATIONS.md#setup-evaluators): [`lower-risk-swing-entry`](../../stages/setup-evaluators/lower-risk-swing-entry.md)
- Benchmark protocol: [`setup-evaluator-forward-outcome-benchmark`](../../backtests/components/setup-evaluators/setup-evaluator-forward-outcome-benchmark.md)
- [Evaluation plan](../../stages/OPERATIONS.md#evaluation-plans): [`lower-risk-swing-entry-iteration-plan`](../../configuration/evaluations/setup-evaluators/lower-risk-swing-entry-iteration-plan.md)
- Previous baseline: [`lower-risk-swing-entry-baseline-current-stop`](lower-risk-swing-entry-baseline-current-stop.md)
- Previous stop-model results: [`lower-risk-swing-entry-stop-model-sweep`](lower-risk-swing-entry-stop-model-sweep.md)

## Root Cause: Buy Limit Placement

### Pre-Experiment Behavior

```python
def constructive_buy_limit(current: Optional[float], support: Optional[float]) -> Optional[float]:
    """Place the buy limit at or near support without chasing distant setups."""
    
    distance_pct = abs(current - support) / current * 100
    if distance_pct <= 1.0:
        return current              # ← Entry at current price (AT support)
    if distance_pct <= 3.0:
        return support + (current - support) * 0.5
    return support
```

**Problem:** When price is within 1% of support, buy_limit = current_price = AT support.

**Example:**
- Current price: $100.00
- Support: $99.96 (0.4% away)
- Buy limit: $100.00 (enters at current, which is AT support)
- Margin of safety: 0.04%

### Evidence from Stop-Model Sweep

For 3,813 "Ready / near buy zone" trades (20-day horizon):

| Metric | Value |
|---|---|
| Entry distance from support (median) | 0.22% |
| Entry distance from support (mean) | 0.40% |
| Stop distance from entry (median) | 3.43% |
| Stop-loss rate | 51.7% |
| Take-profit rate | 19.2% |
| Timeout rate | 29.1% |

**Conclusion:** Even with support-atr-1.5 stops (widest model tested), entries at/near support result in 65% stop-loss rate because normal volatility (3-4% dips) break support immediately.

## Controlled Settings

### Evaluation Window

| Setting | Value |
| --- | --- |
| Evaluation binding | Train/dev partition from the referenced evaluation plan |
| Frequency | `weekly` |
| Horizons | `20`, `40`, `60`, `90`, `120` |
| Historical universe | Removed random-20 fixture; exact tickers remain in the recorded artifact run configurations. |
| Evidence score gate | `70` |
| Setup score threshold | `70` |
| Stop model | `support-atr-1.5` (best from previous sweep) |

## Declared Deltas

### Buy Limit Offset Variants

| Variant | Rule | Margin of Safety | Rationale |
| --- | --- | --- | --- |
| `current` | `buy_limit = current_price` (existing) | 0.04%-0.4% | Baseline for comparison |
| `offset-1` | `buy_limit = support * 0.99` | 1-2% below support | Small pullback requirement |
| `offset-2` | `buy_limit = support * 0.98` | 2-3% below support | Moderate pullback requirement |

**Implementation notes:**
- Modify `constructive_buy_limit()` to accept an offset parameter
- For each offset variant, replace the current branch:
  ```python
  if distance_pct <= 1.0:
      return current  # existing: entry at current
  ```
  With:
  ```python
  if distance_pct <= 1.0:
      return support * (1.0 - offset)  # new: entry below support
  ```
- Keep the 1-3% and >3% branches unchanged (they already use support-relative logic)
- Impact: Lowers entry_score (less proximity to current price), may change setup_status distribution

### Setup Status Threshold Variants

| Variant | Entry Score Threshold | Effect |
| --- | --- | --- |
| `current` | `entry_score >= 18` (existing) | Permits entries at/very-near current |
| `stricter` | `entry_score >= 20` | Rejects shallow entries, requires more pullback |
| `strict` | `entry_score >= 22` | Very restrictive, mostly deep-pullback only |

**Rationale:**
- Current threshold (18) [triggers](../../stages/OPERATIONS.md#trigger) "Ready / near buy zone" when entry_score = 25 (entry = current price)
- Higher thresholds raise the bar for "Ready" status
- May reclassify some setups to "Wait for pullback" instead
- Reduces entered trade count but improves quality

**Implementation notes:**
- Modify line 469 in `lower_risk_swing_entry.py`:
  ```python
  if entry_score >= THRESHOLD and support_score >= 15 and reward_score >= 8:
      return STATUS_READY_NEAR_BUY_ZONE
  ```
- Each threshold should be tested in combination with buy limit offsets

### Experiment Matrix

| Buy Limit Offset | Entry Score Threshold | Scenario ID |
| --- | --- | --- |
| `current` | `current (18)` | `bl-current-es18` |
| `offset-1` | `current (18)` | `bl-offset1-es18` |
| `offset-2` | `current (18)` | `bl-offset2-es18` |
| `current` | `stricter (20)` | `bl-current-es20` |
| `offset-1` | `stricter (20)` | `bl-offset1-es20` |
| `offset-2` | `stricter (20)` | `bl-offset2-es20` |
| `offset-1` | `strict (22)` | `bl-offset1-es22` |
| `offset-2` | `strict (22)` | `bl-offset2-es22` |

**Total runs:** 8 scenarios (2 dimensions)

## Pre-Registered Expectations

### Outcome Expectations

| Dimension | Current (Baseline) | Expected with Offset-2 + ES20 |
| --- | --- | --- |
| Entered trades (20-day) | ~3,800 | ~2,500-3,000 |
| Stop-loss rate | 51.7% | 35-40% |
| Take-profit rate | 19.2% | 25-30% |
| Timeout rate | 29.1% | 30-35% |
| Avg realized return | +0.88% | +1.8-2.2% |
| vs SPY (+2.90%) | -2.02% edge | -0.7-1.1% edge |
| vs universe (+3.81%) | -2.93% edge | -1.6-2.0% edge |

**Rationale:**
- Deeper entries require pullbacks → fewer early-stage signals
- Fewer trades but higher quality → better win rates
- Smaller stop distance from entry → tighter risk (lower max-loss per trade)
- Margin of safety → fewer whipsaw exits
- Still underperforms benchmarks (structural issue), but moves in right direction

## Success Criteria

✅ **Primary:** Stop-loss rate drops below 45% (target: 35-40%)

✅ **Secondary:** Average realized return improves to +1.5% or better (target: +1.8-2.2%)

✅ **Tertiary:** Win rate improves to 35%+ (up from current ~30%)

⚠️ **Acceptable trade-off:** Entered trade count may drop 20-30% (more selective entry)

🚫 **Unacceptable:** Return edge vs SPY worse than -1.5% (current is -2.02%)

## Comparison Framework

### Against Stop-Model Sweep

| Finding | Stop-Model Sweep | This Experiment |
| --- | --- | --- |
| Primary lever | Stop width | Entry depth |
| SL rate improvement | 79% → 65% (14 pp) | Expected: 52% → 38% (14 pp) |
| Return improvement | 0.78% → 1.26% (48 bps) | Expected: 0.88% → 2.00%+ (112+ bps) |
| Approach | Defensive (widen exit) | Offensive (improve entry) |

### Hypothetical Combination

If both improvements stack:
- Stop-model alone: 14 pp SL reduction + 48 bps return
- Entry quality alone: Expected 14 pp SL reduction + 112 bps return
- Combined: 28 pp SL reduction (52% → 24%), +160 bps return (0.88% → 2.48%)

**Note:** Improvements may not be fully additive if stop model and entry quality are correlated, but directional expectation is clear.

## Follow-up

Do not move these variants to validation. If research continues, test whether
support confirmation or the setup-admission rules have predictive value while
holding the current buy-limit behavior fixed. Do not combine another entry
offset with stop/take-profit tuning until an independently useful signal-quality
change is found.

## Implementation Checklist

- [x] Modify `constructive_buy_limit()` to accept `offset` parameter
- [x] Add `entry_score_threshold` parameter to `setup_status()` function
- [x] Update setup evaluator adapter to expose both parameters as backtest CLI args
- [x] Test with `--buy-limit-offset 0.00|0.01|0.02` and `--entry-score-threshold 18|20|22`
- [x] Run all 8 scenarios with same universe/horizon/evaluation window
- [x] Generate outcomes, predictions, summary CSVs for each scenario
- [x] Aggregate results into comparison table
- [x] Document findings and recommendation for next iteration

## Run Index

| Scenario | Artifact directory |
| --- | --- |
| `bl-current-es18` | [`20260723-092835Z__lower-risk-swing-entry__buy-limit-sweep-20-train-dev-bl-current-es18__94374b24`](../../artifacts/stock/backtests/components/setup-evaluators/setup-signal-backtest/20260723-092835Z__lower-risk-swing-entry__buy-limit-sweep-20-train-dev-bl-current-es18__94374b24/) |
| `bl-offset1-es18` | [`20260723-093019Z__lower-risk-swing-entry__buy-limit-sweep-20-train-dev-bl-offset1-es18__1c85adad`](../../artifacts/stock/backtests/components/setup-evaluators/setup-signal-backtest/20260723-093019Z__lower-risk-swing-entry__buy-limit-sweep-20-train-dev-bl-offset1-es18__1c85adad/) |
| `bl-offset2-es18` | [`20260723-093207Z__lower-risk-swing-entry__buy-limit-sweep-20-train-dev-bl-offset2-es18__00b92c2c`](../../artifacts/stock/backtests/components/setup-evaluators/setup-signal-backtest/20260723-093207Z__lower-risk-swing-entry__buy-limit-sweep-20-train-dev-bl-offset2-es18__00b92c2c/) |
| `bl-current-es20` | [`20260723-093311Z__lower-risk-swing-entry__buy-limit-sweep-20-train-dev-bl-current-es20__78210813`](../../artifacts/stock/backtests/components/setup-evaluators/setup-signal-backtest/20260723-093311Z__lower-risk-swing-entry__buy-limit-sweep-20-train-dev-bl-current-es20__78210813/) |
| `bl-offset1-es20` | [`20260723-093459Z__lower-risk-swing-entry__buy-limit-sweep-20-train-dev-bl-offset1-es20__c779e25e`](../../artifacts/stock/backtests/components/setup-evaluators/setup-signal-backtest/20260723-093459Z__lower-risk-swing-entry__buy-limit-sweep-20-train-dev-bl-offset1-es20__c779e25e/) |
| `bl-offset2-es20` | [`20260723-093635Z__lower-risk-swing-entry__buy-limit-sweep-20-train-dev-bl-offset2-es20__7daebc78`](../../artifacts/stock/backtests/components/setup-evaluators/setup-signal-backtest/20260723-093635Z__lower-risk-swing-entry__buy-limit-sweep-20-train-dev-bl-offset2-es20__7daebc78/) |
| `bl-offset1-es22` | [`20260723-093732Z__lower-risk-swing-entry__buy-limit-sweep-20-train-dev-bl-offset1-es22__3b5a02b4`](../../artifacts/stock/backtests/components/setup-evaluators/setup-signal-backtest/20260723-093732Z__lower-risk-swing-entry__buy-limit-sweep-20-train-dev-bl-offset1-es22__3b5a02b4/) |
| `bl-offset2-es22` | [`20260723-093909Z__lower-risk-swing-entry__buy-limit-sweep-20-train-dev-bl-offset2-es22__1a05f6a5`](../../artifacts/stock/backtests/components/setup-evaluators/setup-signal-backtest/20260723-093909Z__lower-risk-swing-entry__buy-limit-sweep-20-train-dev-bl-offset2-es22__1a05f6a5/) |

## Results

Primary 20-trading-day close-entry results:

| Buy-limit variant | Entry threshold | Buy signals | Entered | Win rate | Avg realized | Stop rate | Take-profit rate | Edge vs SPY |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `current` | `18` | 3,813 | 3,763 | 44.96% | 0.88% | 51.71% | 19.16% | -0.15% |
| `offset-1` | `18` | 4,383 | 3,691 | 50.15% | 0.58% | 51.50% | 34.57% | -0.35% |
| `offset-2` | `18` | 1,597 | 1,054 | 44.97% | 0.59% | 50.66% | 20.21% | -0.47% |
| `current` | `20` | 3,813 | 3,763 | 44.96% | 0.88% | 51.71% | 19.16% | -0.15% |
| `offset-1` | `20` | 4,383 | 3,691 | 50.15% | 0.58% | 51.50% | 34.57% | -0.35% |
| `offset-2` | `20` | 474 | 436 | 43.81% | 0.47% | 50.00% | 12.39% | -0.41% |
| `offset-1` | `22` | 4,383 | 3,691 | 50.15% | 0.58% | 51.50% | 34.57% | -0.35% |
| `offset-2` | `22` | 474 | 436 | 43.81% | 0.47% | 50.00% | 12.39% | -0.41% |

Across all five horizons, the current baseline averaged 1.26% realized return
with a 65.72% stop-touch rate. Offset variants averaged 0.77% to 0.93% with
64.17% to 66.44% stop-touch rates. Deeper entries therefore did not improve
the cross-horizon result.

## Findings

- The primary stop-rate criterion failed. The best 20-day close-entry stop
  rate was 50.00%, not below 45%.
- The return criterion failed. Every offset variant produced only 0.47% to
  0.59% average realized return versus the required 1.5% and the 0.88%
  current-entry baseline.
- `offset-1` increased the number of qualifying signals because the deeper
  entry improved reward/risk enough to admit additional setups; selectivity did
  not improve.
- `offset-2` combined with threshold 20 or 22 reduced signals to 474, but the
  smaller sample performed worse rather than better.
- Thresholds 20 and 22 were behaviorally identical because entry proximity is
  bucketed at 25, 22, 18, 12, 6, or 0. Threshold 20 and 22 admit the same
  buckets.
- Limit-entry variants were also weaker: offset stop rates ranged from 56.48%
  to 64.07% and average realized returns from 0.24% to 0.45%.

## Decision

Reject all tested buy-limit offsets and stricter ready-status thresholds for
promotion. Preserve the current buy-limit behavior as the comparison baseline;
the evidence does not support entry depth as the cause of the evaluator's high
stop rate.

## Artifact Contract

Generated artifacts will be stored under:
```
artifacts/stock/backtests/components/setup-evaluators/setup-signal-backtest/
  <timestamp>__lower-risk-swing-entry__buy-limit-sweep-20-train-dev-<scenario>__<config-hash>/
```

Each scenario will include:
- `predictions.csv`: Point-in-time setup signals with buy limits, stops, TP, scores
- `outcomes.csv`: Trade outcomes (entry/exit, returns, exits reasons, MAE/MFE)
- `summary.csv`: Aggregated statistics by horizon, action, setup score, setup status
- `execution-report.md`: Backtest run parameters, [execution](../../stages/OPERATIONS.md#execution-and-execution-models) notes, data quality
- `run_config.csv`: Exact parameters used (buy_limit_offset, entry_score_threshold, etc.)

## Related Decisions

**From stop-model sweep decision (line 100-102):**
> Use `support-atr-1.5` as the provisional stop model for the next train/dev
> iteration because it is clearly better than the current stop model, but treat
> it as only one part of the fix.

**Recommendation:** Fix buy limit placement first, then hold stop model constant.

## References

- Setup evaluator implementation: `stages/setup-evaluators/lower_risk_swing_entry.py`
- Entry proximity scoring: `entry_proximity_score`
- Support quality scoring: `support_quality_score`
- Setup status logic: `setup_status`
- Buy-limit construction: `constructive_buy_limit`
- Invalidation level: `invalidation_level`

## Open Questions

1. **Should buy-limit offsets vary by support type?**
   - E.g., require deeper offset for "recent support" vs moving average support?
   - Current design applies same offset to all support types
   - Could refine in post-experiment iteration

2. **Should entry-score threshold interact with take-profit distance?**
   - Current design changes only entry_score threshold
   - Wider entries might need farther TP targets to maintain R/R
   - May need co-optimization; testing separately for now

3. **What if setup-status reclassification reduces trade count too much?**
   - E.g., if offset-2 + ES22 results in only 1,000 trades (73% fewer)
   - Return improves but sample size is small
   - Will accept trade-offs but document them clearly
