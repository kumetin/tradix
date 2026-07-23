#!/usr/bin/env python3
"""Deterministic setup construction and scoring for lower-risk swing entries.

Parameters:
    Public methods accept typed setup inputs, point-in-time price/indicator
    sequences, optional analyst evidence, and scoring or risk-model values.
External sources:
    None. Callers supply all market and analyst observations; this module does
    not read files or contact services.
Side effects:
    None. Construction and scoring return values without mutating external
    state.
Examples:
    Score an already classified setup::

        result = LowerRiskSwingEntryEvaluator.evaluate(LowerRiskSwingEntryInputs(...))

    Build setup levels from point-in-time observations::

        setup = LowerRiskSwingEntryEvaluator.construct_setup(...)

The public flow is:

1. Build a setup with ``LowerRiskSwingEntryEvaluator.construct_setup(...)``.
2. Score one setup with ``evaluate(...)`` or a batch with ``score_setups(...)``.

The module deliberately separates setup construction from scoring so backtests
can reuse the same support, resistance, stop, reward/risk, setup-score, and evidence-score
logic that the markdown evaluator expects.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Dict, List, Optional, Sequence, Tuple


SUPPORT_CONFLUENCE_WITHIN_3PCT = "confluence_within_3pct"
SUPPORT_STRONG_WITHIN_3PCT = "strong_within_3pct"
SUPPORT_WITHIN_3_TO_6PCT = "support_within_3_to_6pct"
SUPPORT_WEAK_OR_DISTANT = "weak_or_distant"
SUPPORT_NONE = "none"

TREND_CONSTRUCTIVE_ABOVE_RISING_AVERAGES = "constructive_above_rising_averages"
TREND_CONSTRUCTIVE_MIXED_SLOPE = "constructive_mixed_slope"
TREND_CHOPPY_OR_WEAK = "choppy_or_weak"
TREND_DAMAGED = "damaged"

ANALYST_STRONG = "strong"
ANALYST_STABLE = "stable"
ANALYST_THIN_OR_MODEST = "thin_or_modest"
ANALYST_WEAK_OR_MISSING = "weak_or_missing"

EXTENSION_LOW = "low"
EXTENSION_MODERATE = "moderate"
EXTENSION_HIGH = "high"
EXTENSION_SEVERE = "severe"

PRICE_DATA_CURRENT = "current"
PRICE_DATA_PARTIAL = "partial"
PRICE_DATA_MISSING = "missing"

LEVELS_OBJECTIVE = "objective"
LEVELS_APPROXIMATE = "approximate"
LEVELS_MISSING = "missing"

INDICATORS_COMPLETE = "complete"
INDICATORS_MOSTLY_COMPLETE = "mostly_complete"
INDICATORS_SPARSE = "sparse"
INDICATORS_MISSING = "missing"

ANALYST_DATA_COMPLETE = "complete"
ANALYST_DATA_TARGET_AND_COUNT = "target_and_count"
ANALYST_DATA_TARGET_ONLY = "target_only"
ANALYST_DATA_MISSING = "missing"

TRADE_MATH_RECONCILES = "reconciles"
TRADE_MATH_ESTIMATED = "estimated"
TRADE_MATH_UNVERIFIED = "unverified"

RECENCY_CLEAN = "clean"
RECENCY_MINOR_UNCERTAINTY = "minor_uncertainty"
RECENCY_STALE_OR_EVENT_GAP = "stale_or_event_gap"

STATUS_READY_NEAR_BUY_ZONE = "Ready / near buy zone"
STATUS_WAIT_FOR_PULLBACK = "Wait for pullback"
STATUS_WATCH_BREAKOUT_RETEST = "Watch breakout retest"
STATUS_TOO_EXTENDED = "Too extended"
STATUS_WEAK_ANALYST_SUPPORT = "Weak analyst support"
STATUS_AVOID_FOR_NOW = "Avoid for now"

ATR_WINDOW = 14
INITIAL_INVALIDATION_ATR_MULTIPLE = 0.8
FALLBACK_INVALIDATION_PCT = 0.015
TRAILING_STOP_ATR_MULTIPLE = 2.0
MIN_TRAILING_STOP_PCT = 0.045
MAX_TRAILING_STOP_PCT = 0.12


@dataclass(frozen=True)
class LowerRiskSwingEntryInputs:
    """Normalized component inputs consumed by the scoring function.

    Callers normally should not build this directly. Prefer
    ``construct_setup(...)``, which derives these fields from feature rows and
    trade-construction rules. Direct construction is useful only when a caller
    has already produced support, reward/risk, trend, analyst, and data-quality
    classifications with the same definitions.
    """

    current_price: Optional[float]
    buy_limit: Optional[float]
    reward_risk: Optional[float]
    support_quality: str
    trend_structure: str
    analyst_support: str
    extension_risk: str
    price_data_quality: str
    support_resistance_quality: str
    indicator_quality: str
    analyst_data_quality: str
    trade_math_quality: str
    recency_gap_risk: str


@dataclass(frozen=True)
class LowerRiskSwingEntrySetup:
    """Constructed trade setup plus the normalized inputs used for scoring."""

    ticker: str
    latest_date: str
    current_price: Optional[float]
    setup_type: str
    key_support: Optional[float]
    key_resistance: Optional[float]
    buy_limit: Optional[float]
    trailing_stop_amount: Optional[float]
    trailing_stop_pct: Optional[float]
    invalidation_level: Optional[float]
    take_profit: Optional[float]
    reward_risk: Optional[float]
    inputs: LowerRiskSwingEntryInputs


@dataclass(frozen=True)
class LowerRiskSwingEntryEvaluation:
    """Deterministic setup score, evidence score, and status for one setup."""

    setup_score: int
    setup_score_breakdown: Dict[str, int]
    setup_status: str
    evidence_score: int
    evidence_score_breakdown: Dict[str, int]
    reasons: Tuple[str, ...]

    def setup_score_breakdown_text(self) -> str:
        return format_breakdown("SS", self.setup_score, self.setup_score_breakdown, ("EP", "SQ", "RR", "TS", "AS", "ER"))

    def evidence_score_breakdown_text(self) -> str:
        return format_breakdown(
            "ES",
            self.evidence_score,
            self.evidence_score_breakdown,
            ("PD", "SR", "MA", "AD", "TM", "RG"),
        )


@dataclass(frozen=True)
class LowerRiskSwingEntryScoredSetup:
    """Keeps a constructed setup aligned with its deterministic evaluation."""

    setup: LowerRiskSwingEntrySetup
    evaluation: LowerRiskSwingEntryEvaluation


class LowerRiskSwingEntryEvaluator:
    """Public API for constructing, scoring, and ranking swing-entry setups."""

    @staticmethod
    def construct_setup(
        ticker: str,
        feature_rows: Sequence[Dict[str, str]],
        analyst_support: str = ANALYST_WEAK_OR_MISSING,
        analyst_data_quality: str = ANALYST_DATA_MISSING,
        recency_gap_risk: str = RECENCY_CLEAN,
        buy_limit_offset: float = 0.0,
    ) -> LowerRiskSwingEntrySetup:
        """Construct a deterministic setup from daily feature rows.

        ``feature_rows`` should be point-in-time rows up to the evaluation date.
        The latest row becomes the decision row. The constructor derives:

        - support from nearby moving averages and recent lows
        - resistance from the trailing 252-row adjusted high
        - buy limit from the relationship between current price and support
        - trailing stop from ATR with min/max risk-management bounds
        - initial invalidation from support minus an ATR buffer
        - reward/risk from buy limit, invalidation, and take-profit

        Analyst fields are optional classifications supplied by the caller.
        They default to missing/unavailable so the function never fabricates
        analyst support.
        """

        rows = [row for row in feature_rows if to_float(row.get("adj_close")) is not None]
        rows = sorted(rows, key=lambda row: row.get("date", ""))
        if not rows:
            return empty_setup(ticker)

        latest = rows[-1]
        current = to_float(latest.get("adj_close"))
        support, support_label = constructive_support(latest, rows)
        resistance = constructive_resistance(latest, rows)
        buy_limit = constructive_buy_limit(current, support, buy_limit_offset)
        atr = average_true_range(rows, ATR_WINDOW)
        trailing_pct = trailing_stop_pct(rows, atr)
        trailing_amount = current * trailing_pct if current is not None else None
        invalidation = invalidation_level(buy_limit, support, atr)
        take_profit = resistance
        reward_risk = reward_risk_ratio(buy_limit, invalidation, take_profit)

        inputs = LowerRiskSwingEntryInputs(
            current_price=current,
            buy_limit=buy_limit,
            reward_risk=reward_risk,
            support_quality=constructed_support_quality(current, support, latest),
            trend_structure=constructed_trend_structure(latest, rows),
            analyst_support=analyst_support,
            extension_risk=constructed_extension_risk(latest),
            price_data_quality=PRICE_DATA_CURRENT if current is not None else PRICE_DATA_MISSING,
            support_resistance_quality=LEVELS_OBJECTIVE if support is not None and resistance is not None else LEVELS_MISSING,
            indicator_quality=constructed_indicator_quality(latest),
            analyst_data_quality=analyst_data_quality,
            trade_math_quality=TRADE_MATH_RECONCILES if reward_risk is not None else TRADE_MATH_UNVERIFIED,
            recency_gap_risk=recency_gap_risk,
        )
        return LowerRiskSwingEntrySetup(
            ticker=ticker.upper(),
            latest_date=latest.get("date", ""),
            current_price=current,
            setup_type=support_label,
            key_support=support,
            key_resistance=resistance,
            buy_limit=buy_limit,
            trailing_stop_amount=trailing_amount,
            trailing_stop_pct=trailing_pct,
            invalidation_level=invalidation,
            take_profit=take_profit,
            reward_risk=reward_risk,
            inputs=inputs,
        )

    @staticmethod
    def evaluate(
        inputs: LowerRiskSwingEntryInputs,
        entry_score_threshold: int = 18,
    ) -> LowerRiskSwingEntryEvaluation:
        """Score one normalized setup input set.

        This method is intentionally pure and deterministic. It does not derive
        trade levels; it only turns already-normalized classifications into the
        setup score, evidence score, and setup status.
        """

        setup_score_breakdown = {
            "EP": entry_proximity_score(inputs.current_price, inputs.buy_limit),
            "SQ": support_quality_score(inputs.support_quality),
            "RR": reward_risk_score(inputs.reward_risk),
            "TS": trend_structure_score(inputs.trend_structure),
            "AS": analyst_support_score(inputs.analyst_support),
            "ER": extension_risk_score(inputs.extension_risk),
        }
        evidence_score_breakdown = {
            "PD": price_data_quality_score(inputs.price_data_quality),
            "SR": support_resistance_quality_score(inputs.support_resistance_quality),
            "MA": indicator_quality_score(inputs.indicator_quality),
            "AD": analyst_data_quality_score(inputs.analyst_data_quality),
            "TM": trade_math_quality_score(inputs.trade_math_quality),
            "RG": recency_gap_risk_score(inputs.recency_gap_risk),
        }
        status = setup_status(
            inputs,
            setup_score_breakdown,
            evidence_score_breakdown,
            entry_score_threshold,
        )
        reasons = (
            f"status:{status}",
            *(f"setup:{key}={value}" for key, value in setup_score_breakdown.items()),
            *(f"evidence:{key}={value}" for key, value in evidence_score_breakdown.items()),
        )
        return LowerRiskSwingEntryEvaluation(
            setup_score=sum(setup_score_breakdown.values()),
            setup_score_breakdown=setup_score_breakdown,
            setup_status=status,
            evidence_score=sum(evidence_score_breakdown.values()),
            evidence_score_breakdown=evidence_score_breakdown,
            reasons=reasons,
        )

    @staticmethod
    def score(
        inputs: List[LowerRiskSwingEntryInputs],
        entry_score_threshold: int = 18,
    ) -> List[LowerRiskSwingEntryEvaluation]:
        """Score and sort normalized inputs without preserving setup fields.

        Prefer ``score_setups(...)`` for table output because it keeps ticker,
        support, resistance, buy limit, and stop fields attached to each scored
        evaluation.
        """

        evaluations = [
            LowerRiskSwingEntryEvaluator.evaluate(item, entry_score_threshold)
            for item in inputs
        ]
        indexed = list(enumerate(evaluations))
        indexed.sort(
            key=lambda item: (
                item[1].setup_score,
                item[1].evidence_score,
                inputs[item[0]].reward_risk if inputs[item[0]].reward_risk is not None else -1.0,
            ),
            reverse=True,
        )
        return [evaluation for _, evaluation in indexed]

    @staticmethod
    def score_setups(
        setups: List[LowerRiskSwingEntrySetup],
        entry_score_threshold: int = 18,
    ) -> List[LowerRiskSwingEntryScoredSetup]:
        """Score and sort constructed setups while preserving setup details."""

        pairs = [
            (
                setup,
                LowerRiskSwingEntryEvaluator.evaluate(
                    setup.inputs,
                    entry_score_threshold,
                ),
            )
            for setup in setups
        ]
        pairs.sort(
            key=lambda item: (
                item[1].setup_score,
                item[1].evidence_score,
                item[0].reward_risk if item[0].reward_risk is not None else -1.0,
            ),
            reverse=True,
        )
        return [
            LowerRiskSwingEntryScoredSetup(setup=setup, evaluation=evaluation)
            for setup, evaluation in pairs
        ]


def entry_proximity_score(current_price: Optional[float], buy_limit: Optional[float]) -> int:
    """Score how close the current price is to the intended buy limit."""

    if current_price is None or buy_limit is None or current_price <= 0:
        return 0
    distance_pct = abs(current_price - buy_limit) / current_price * 100
    if distance_pct <= 1:
        return 25
    if distance_pct <= 2:
        return 22
    if distance_pct <= 3:
        return 18
    if distance_pct <= 5:
        return 12
    if distance_pct <= 8:
        return 6
    return 0


def support_quality_score(value: str) -> int:
    """Map support-quality classification to setup-score points."""

    return {
        SUPPORT_CONFLUENCE_WITHIN_3PCT: 20,
        SUPPORT_STRONG_WITHIN_3PCT: 15,
        SUPPORT_WITHIN_3_TO_6PCT: 10,
        SUPPORT_WEAK_OR_DISTANT: 5,
        SUPPORT_NONE: 0,
    }.get(value, 0)


def reward_risk_score(reward_risk: Optional[float]) -> int:
    """Score reward/risk using fixed buckets from the evaluator rubric."""

    if reward_risk is None:
        return 0
    if reward_risk >= 3.0:
        return 20
    if reward_risk >= 2.5:
        return 17
    if reward_risk >= 2.0:
        return 13
    if reward_risk >= 1.8:
        return 8
    return 0


def trend_structure_score(value: str) -> int:
    """Map trend-structure classification to setup-score points."""

    return {
        TREND_CONSTRUCTIVE_ABOVE_RISING_AVERAGES: 15,
        TREND_CONSTRUCTIVE_MIXED_SLOPE: 10,
        TREND_CHOPPY_OR_WEAK: 5,
        TREND_DAMAGED: 0,
    }.get(value, 0)


def analyst_support_score(value: str) -> int:
    """Map analyst-support classification to setup-score points."""

    return {
        ANALYST_STRONG: 10,
        ANALYST_STABLE: 7,
        ANALYST_THIN_OR_MODEST: 4,
        ANALYST_WEAK_OR_MISSING: 0,
    }.get(value, 0)


def extension_risk_score(value: str) -> int:
    """Map extension-risk classification to setup-score points."""

    return {
        EXTENSION_LOW: 10,
        EXTENSION_MODERATE: 7,
        EXTENSION_HIGH: 3,
        EXTENSION_SEVERE: 0,
    }.get(value, 0)


def price_data_quality_score(value: str) -> int:
    """Map price-data quality classification to evidence-score points."""

    return {
        PRICE_DATA_CURRENT: 20,
        PRICE_DATA_PARTIAL: 12,
        PRICE_DATA_MISSING: 0,
    }.get(value, 0)


def support_resistance_quality_score(value: str) -> int:
    """Map support/resistance objectivity to evidence-score points."""

    return {
        LEVELS_OBJECTIVE: 15,
        LEVELS_APPROXIMATE: 8,
        LEVELS_MISSING: 0,
    }.get(value, 0)


def indicator_quality_score(value: str) -> int:
    """Map indicator completeness to evidence-score points."""

    return {
        INDICATORS_COMPLETE: 15,
        INDICATORS_MOSTLY_COMPLETE: 10,
        INDICATORS_SPARSE: 5,
        INDICATORS_MISSING: 0,
    }.get(value, 0)


def analyst_data_quality_score(value: str) -> int:
    """Map analyst-data completeness to evidence-score points."""

    return {
        ANALYST_DATA_COMPLETE: 20,
        ANALYST_DATA_TARGET_AND_COUNT: 12,
        ANALYST_DATA_TARGET_ONLY: 6,
        ANALYST_DATA_MISSING: 0,
    }.get(value, 0)


def trade_math_quality_score(value: str) -> int:
    """Map trade-math consistency to evidence-score points."""

    return {
        TRADE_MATH_RECONCILES: 20,
        TRADE_MATH_ESTIMATED: 10,
        TRADE_MATH_UNVERIFIED: 0,
    }.get(value, 0)


def recency_gap_risk_score(value: str) -> int:
    """Map recency and event-gap quality to evidence-score points."""

    return {
        RECENCY_CLEAN: 10,
        RECENCY_MINOR_UNCERTAINTY: 5,
        RECENCY_STALE_OR_EVENT_GAP: 0,
    }.get(value, 0)


def setup_status(
    inputs: LowerRiskSwingEntryInputs,
    setup_score_breakdown: Dict[str, int],
    evidence_score_breakdown: Dict[str, int],
    entry_score_threshold: int = 18,
) -> str:
    """Derive the table setup status from score components and data quality."""

    evidence_score = sum(evidence_score_breakdown.values())
    reward_score = setup_score_breakdown["RR"]
    entry_score = setup_score_breakdown["EP"]
    support_score = setup_score_breakdown["SQ"]
    trend_score = setup_score_breakdown["TS"]
    analyst_score = setup_score_breakdown["AS"]
    extension_score = setup_score_breakdown["ER"]

    if evidence_score < 50 or inputs.current_price is None or inputs.buy_limit is None:
        return STATUS_AVOID_FOR_NOW
    if extension_score == 0:
        return STATUS_TOO_EXTENDED
    if analyst_score == 0 and inputs.analyst_data_quality != ANALYST_DATA_MISSING:
        return STATUS_WEAK_ANALYST_SUPPORT
    if entry_score >= entry_score_threshold and support_score >= 15 and reward_score >= 8:
        return STATUS_READY_NEAR_BUY_ZONE
    if reward_score == 0:
        return STATUS_AVOID_FOR_NOW
    if entry_score <= 12 and support_score >= 10:
        return STATUS_WAIT_FOR_PULLBACK
    if trend_score >= 10:
        return STATUS_WATCH_BREAKOUT_RETEST
    return STATUS_AVOID_FOR_NOW


def format_breakdown(total_key: str, total: int, components: Dict[str, int], order: Tuple[str, ...]) -> str:
    """Format score components as a stable semicolon-delimited string."""

    parts = [f"{total_key}={total}"]
    parts.extend(f"{key}={components[key]}" for key in order)
    return "; ".join(parts)


def empty_setup(ticker: str) -> LowerRiskSwingEntrySetup:
    """Return a fully missing setup for symbols without usable feature rows."""

    inputs = LowerRiskSwingEntryInputs(
        current_price=None,
        buy_limit=None,
        reward_risk=None,
        support_quality=SUPPORT_NONE,
        trend_structure=TREND_DAMAGED,
        analyst_support=ANALYST_WEAK_OR_MISSING,
        extension_risk=EXTENSION_SEVERE,
        price_data_quality=PRICE_DATA_MISSING,
        support_resistance_quality=LEVELS_MISSING,
        indicator_quality=INDICATORS_MISSING,
        analyst_data_quality=ANALYST_DATA_MISSING,
        trade_math_quality=TRADE_MATH_UNVERIFIED,
        recency_gap_risk=RECENCY_STALE_OR_EVENT_GAP,
    )
    return LowerRiskSwingEntrySetup(
        ticker=ticker.upper(),
        latest_date="",
        current_price=None,
        setup_type="N/A",
        key_support=None,
        key_resistance=None,
        buy_limit=None,
        trailing_stop_amount=None,
        trailing_stop_pct=None,
        invalidation_level=None,
        take_profit=None,
        reward_risk=None,
        inputs=inputs,
    )


def constructive_support(latest: Dict[str, str], rows: Sequence[Dict[str, str]]) -> Tuple[Optional[float], str]:
    """Select the nearest constructive support from MAs and recent lows."""

    current = to_float(latest.get("adj_close"))
    if current is None:
        return None, "N/A"
    candidates = []
    for label, column in (
        ("Pullback at 20-EMA", "sma_20"),
        ("Pullback at 50-SMA", "sma_50"),
        ("Pullback at 150-SMA", "sma_150"),
        ("Pullback at 200-SMA", "sma_200"),
    ):
        value = to_float(latest.get(column))
        if value is not None and value <= current * 1.01:
            candidates.append((abs(current - value) / current, value, label))
    recent_lows = [to_float(row.get("adj_low")) for row in rows[-21:]]
    lows_below = [value for value in recent_lows if value is not None and value <= current]
    if lows_below:
        value = max(lows_below)
        candidates.append((abs(current - value) / current, value, "Pullback at recent support"))
    if not candidates:
        return None, "N/A"
    _, support, label = min(candidates, key=lambda item: item[0])
    return support, label


def constructive_resistance(latest: Dict[str, str], rows: Sequence[Dict[str, str]]) -> Optional[float]:
    """Use the trailing 252-row adjusted high as the take-profit reference."""

    current = to_float(latest.get("adj_close"))
    values = [to_float(row.get("adj_high")) for row in rows[-252:]]
    highs = [value for value in values if value is not None]
    if not highs:
        return None
    resistance = max(highs)
    if current is not None and resistance <= current:
        high_252 = to_float(latest.get("high_252"))
        if high_252 is not None:
            resistance = max(resistance, high_252)
    return resistance


def constructive_buy_limit(
    current: Optional[float],
    support: Optional[float],
    offset: float = 0.0,
) -> Optional[float]:
    """Place the buy limit at or near support without chasing distant setups."""

    if current is None or support is None:
        return None
    if offset < 0 or offset >= 1:
        raise ValueError("buy-limit offset must be in [0, 1)")
    distance_pct = abs(current - support) / current * 100
    if distance_pct <= 1.0:
        return current if offset == 0 else support * (1.0 - offset)
    if distance_pct <= 3.0:
        return support + (current - support) * 0.5
    return support


def trailing_stop_pct(rows: Sequence[Dict[str, str]], atr: Optional[float] = None) -> Optional[float]:
    """Compute a trailing stop percentage from ATR with risk-management bounds.

    The minimum and maximum percentages are gates for order management. They do
    not define the initial invalidation level, which is support-anchored.
    """

    if atr is None:
        atr = average_true_range(rows, ATR_WINDOW)
    current = to_float(rows[-1].get("adj_close")) if rows else None
    if atr is None or current is None or current <= 0:
        return None
    atr_pct = atr / current
    return max(MIN_TRAILING_STOP_PCT, min(MAX_TRAILING_STOP_PCT, atr_pct * TRAILING_STOP_ATR_MULTIPLE))


def average_true_range(rows: Sequence[Dict[str, str]], window: int) -> Optional[float]:
    """Compute ATR from adjusted high, adjusted low, and adjusted close."""

    if len(rows) < window + 1:
        return None
    ranges = []
    tail = rows[-window:]
    previous = rows[-window - 1]
    previous_close = to_float(previous.get("adj_close"))
    for row in tail:
        high = to_float(row.get("adj_high"))
        low = to_float(row.get("adj_low"))
        if high is None or low is None or previous_close is None:
            return None
        ranges.append(max(high - low, abs(high - previous_close), abs(low - previous_close)))
        previous_close = to_float(row.get("adj_close"))
    return sum(ranges) / len(ranges) if ranges else None


def invalidation_level(
    buy_limit: Optional[float],
    support: Optional[float],
    atr: Optional[float],
) -> Optional[float]:
    """Set initial invalidation below support with an ATR buffer.

    This is the setup-failure reference, not the trailing-stop amount. ATR is
    preferred because support breaks need enough volatility buffer to avoid
    classifying normal noise as invalidation. A small percentage fallback is
    used only when ATR is unavailable.
    """

    if buy_limit is None or support is None:
        return None
    if atr is not None and atr > 0:
        support_buffer = atr * INITIAL_INVALIDATION_ATR_MULTIPLE
    else:
        support_buffer = support * FALLBACK_INVALIDATION_PCT
    return support - support_buffer


def reward_risk_ratio(
    buy_limit: Optional[float],
    invalidation: Optional[float],
    take_profit: Optional[float],
) -> Optional[float]:
    """Compute reward/risk from buy limit, invalidation, and take-profit."""

    if buy_limit is None or invalidation is None or take_profit is None:
        return None
    risk = buy_limit - invalidation
    reward = take_profit - buy_limit
    if risk <= 0 or reward <= 0:
        return None
    return reward / risk


def constructed_support_quality(current: Optional[float], support: Optional[float], latest: Dict[str, str]) -> str:
    """Classify support quality using distance and moving-average confluence."""

    if current is None or support is None:
        return SUPPORT_NONE
    distance_pct = abs(current - support) / current * 100
    ma_values = [to_float(latest.get(column)) for column in ("sma_20", "sma_50", "sma_150", "sma_200")]
    has_ma_confluence = any(value is not None and abs(value - support) / current * 100 <= 1.0 for value in ma_values)
    if distance_pct <= 3 and has_ma_confluence:
        return SUPPORT_CONFLUENCE_WITHIN_3PCT
    if distance_pct <= 3:
        return SUPPORT_STRONG_WITHIN_3PCT
    if distance_pct <= 6:
        return SUPPORT_WITHIN_3_TO_6PCT
    return SUPPORT_WEAK_OR_DISTANT


def constructed_trend_structure(latest: Dict[str, str], rows: Sequence[Dict[str, str]]) -> str:
    """Classify trend from price position and moving-average slopes."""

    current = to_float(latest.get("adj_close"))
    sma50 = to_float(latest.get("sma_50"))
    sma150 = to_float(latest.get("sma_150"))
    sma200 = to_float(latest.get("sma_200"))
    s50 = moving_average_slope(rows, "sma_50")
    s150 = moving_average_slope(rows, "sma_150")
    if current is None or sma50 is None:
        return TREND_CHOPPY_OR_WEAK
    above_long = current > sma50 and ((sma150 is not None and current > sma150) or (sma200 is not None and current > sma200))
    rising = (s50 is not None and s50 > 0) and (s150 is not None and s150 > 0)
    if above_long and rising:
        return TREND_CONSTRUCTIVE_ABOVE_RISING_AVERAGES
    if current > sma50 or (sma150 is not None and current > sma150):
        return TREND_CONSTRUCTIVE_MIXED_SLOPE
    if sma200 is not None and current < sma200:
        return TREND_DAMAGED
    return TREND_CHOPPY_OR_WEAK


def moving_average_slope(rows: Sequence[Dict[str, str]], column: str, lookback: int = 20) -> Optional[float]:
    """Return simple slope over ``lookback`` rows for a moving-average column."""

    if len(rows) <= lookback:
        return None
    now = to_float(rows[-1].get(column))
    then = to_float(rows[-1 - lookback].get(column))
    if now is None or then is None:
        return None
    return now - then


def constructed_extension_risk(latest: Dict[str, str]) -> str:
    """Classify whether price is extended above short/intermediate averages."""

    current = to_float(latest.get("adj_close"))
    sma20 = to_float(latest.get("sma_20"))
    sma50 = to_float(latest.get("sma_50"))
    if current is None or sma20 is None or sma50 is None:
        return EXTENSION_SEVERE
    above20 = percent_above(current, sma20)
    above50 = percent_above(current, sma50)
    if above20 is not None and above50 is not None and above20 <= 5 and above50 <= 8:
        return EXTENSION_LOW
    if (above20 is not None and above20 <= 8) or (above50 is not None and above50 <= 12):
        return EXTENSION_MODERATE
    if above50 is not None and above50 <= 15:
        return EXTENSION_HIGH
    return EXTENSION_SEVERE


def constructed_indicator_quality(latest: Dict[str, str]) -> str:
    """Classify local indicator completeness on the latest feature row."""

    required = ("sma_20", "sma_50", "sma_150", "sma_200", "ret_21", "ret_63", "dd_252")
    missing = sum(1 for column in required if to_float(latest.get(column)) is None)
    if missing == 0:
        return INDICATORS_COMPLETE
    if missing <= 2:
        return INDICATORS_MOSTLY_COMPLETE
    if missing < len(required):
        return INDICATORS_SPARSE
    return INDICATORS_MISSING


def percent_above(value: Optional[float], baseline: Optional[float]) -> Optional[float]:
    """Return percentage difference from baseline, or ``None`` if invalid."""

    if value is None or baseline is None or baseline == 0:
        return None
    return (value - baseline) / baseline * 100


def to_float(value: Optional[str]) -> Optional[float]:
    """Parse optional CSV string values into floats."""

    if value in (None, ""):
        return None
    try:
        return float(value)
    except ValueError:
        return None
