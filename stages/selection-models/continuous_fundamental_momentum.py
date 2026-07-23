"""Point-in-time continuous fundamental and momentum selection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


FUNDAMENTAL_FIELDS = (
    "is_eps_growing",
    "is_profit_margins_increasing",
    "is_revenue_rises",
    "is_debt_lowers",
    "is_institutional_accumalation_rising",
)
MINIMUM_KNOWN_FUNDAMENTALS = 4


@dataclass(frozen=True)
class SelectionResult:
    as_of: str
    eligibility: dict[str, dict[str, Any]]
    ranking: tuple[dict[str, Any], ...]
    targets: tuple[dict[str, Any], ...]
    fallback_used: bool


def _boolean(value: Any) -> bool | None:
    if value is True or value == "true":
        return True
    if value is False or value == "false":
        return False
    return None


def _number(value: Any) -> float | None:
    try:
        return None if value in (None, "") else float(value)
    except (TypeError, ValueError):
        return None


def select(
    *,
    as_of: str,
    candidates: Sequence[str],
    features: Mapping[str, Mapping[str, Any]],
    target_count: int = 10,
    fallback_mode: str = "empty",
    fallback_ticker: str | None = None,
) -> SelectionResult:
    """Return equal-weight targets ranked by a frozen continuous score."""
    if target_count < 1:
        raise ValueError("target_count must be positive")
    if fallback_mode not in {"empty", "fallback"}:
        raise ValueError("fallback_mode must be 'empty' or 'fallback'")
    if fallback_mode == "fallback" and not fallback_ticker:
        raise ValueError("fallback_ticker is required in fallback mode")

    eligibility: dict[str, dict[str, Any]] = {}
    eligible: list[tuple[str, float, float, int]] = []
    for instrument_id in candidates:
        row = features.get(instrument_id)
        reasons: list[str] = []
        if row is None:
            reasons.append("missing:feature_row")
        else:
            momentum = _number(row.get("ret_252"))
            values = [_boolean(row.get(field)) for field in FUNDAMENTAL_FIELDS]
            known = [value for value in values if value is not None]
            if momentum is None:
                reasons.append("missing:ret_252")
            if len(known) < MINIMUM_KNOWN_FUNDAMENTALS:
                reasons.append("insufficient:fundamental_evidence")
            if not reasons:
                fundamental_score = sum(known) / len(known)
                eligible.append(
                    (instrument_id, momentum, fundamental_score, len(known))
                )
        eligibility[instrument_id] = {
            "eligible": not reasons,
            "reasons": tuple(reasons),
        }

    momentum_order = sorted(eligible, key=lambda item: (item[1], item[0]))
    count = len(momentum_order)
    percentiles = {
        item[0]: (index / (count - 1) if count > 1 else 1.0)
        for index, item in enumerate(momentum_order)
    }
    scored = [
        (
            instrument_id,
            momentum,
            fundamental_score,
            known_count,
            percentiles[instrument_id],
            0.5 * percentiles[instrument_id] + 0.5 * fundamental_score,
        )
        for instrument_id, momentum, fundamental_score, known_count in eligible
    ]
    scored.sort(key=lambda item: (-item[5], -item[1], item[0]))
    ranking = tuple(
        {
            "instrument_id": item[0],
            "ret_252": item[1],
            "fundamental_score": item[2],
            "known_fundamental_count": item[3],
            "momentum_percentile": item[4],
            "composite_score": item[5],
            "rank": index + 1,
        }
        for index, item in enumerate(scored)
    )
    selected = ranking[:target_count]
    fallback_used = not selected and fallback_mode == "fallback"
    if fallback_used:
        targets = ({"instrument_id": fallback_ticker, "weight": 1.0},)
    else:
        weight = 1.0 / len(selected) if selected else 0.0
        targets = tuple(
            {"instrument_id": item["instrument_id"], "weight": weight}
            for item in selected
        )
    return SelectionResult(as_of, eligibility, ranking, targets, fallback_used)
