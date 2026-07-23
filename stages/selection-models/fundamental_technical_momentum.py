"""Point-in-time fundamental and technical momentum selection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


BOOLEAN_FIELDS = (
    "is_eps_growing",
    "is_profit_margins_increasing",
    "is_revenue_rises",
    "is_debt_lowers",
    "is_institutional_accumalation_rising",
    "is_high_relative_volume",
    "is_above_moving_average",
    "is_relative_strength_high",
)
SEVEN_CONDITION_FIELDS = tuple(
    field for field in BOOLEAN_FIELDS if field != "is_high_relative_volume"
)


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
    """Return deterministic equal-weight targets satisfying every condition."""
    return _select(
        as_of=as_of,
        candidates=candidates,
        features=features,
        required_boolean_fields=BOOLEAN_FIELDS,
        target_count=target_count,
        fallback_mode=fallback_mode,
        fallback_ticker=fallback_ticker,
    )


def select_without_high_relative_volume(
    *,
    as_of: str,
    candidates: Sequence[str],
    features: Mapping[str, Mapping[str, Any]],
    target_count: int = 10,
    fallback_mode: str = "empty",
    fallback_ticker: str | None = None,
) -> SelectionResult:
    """Select using the seven frozen non-volume conditions."""
    return _select(
        as_of=as_of,
        candidates=candidates,
        features=features,
        required_boolean_fields=SEVEN_CONDITION_FIELDS,
        target_count=target_count,
        fallback_mode=fallback_mode,
        fallback_ticker=fallback_ticker,
    )


def _select(
    *,
    as_of: str,
    candidates: Sequence[str],
    features: Mapping[str, Mapping[str, Any]],
    required_boolean_fields: Sequence[str],
    target_count: int,
    fallback_mode: str,
    fallback_ticker: str | None,
) -> SelectionResult:
    if target_count < 1:
        raise ValueError("target_count must be positive")
    if fallback_mode not in {"empty", "fallback"}:
        raise ValueError("fallback_mode must be 'empty' or 'fallback'")
    if fallback_mode == "fallback" and not fallback_ticker:
        raise ValueError("fallback_ticker is required in fallback mode")

    eligibility: dict[str, dict[str, Any]] = {}
    eligible: list[tuple[str, float, float]] = []
    for instrument_id in candidates:
        row = features.get(instrument_id)
        reasons: list[str] = []
        if row is None:
            reasons.append("missing:feature_row")
        else:
            for field in required_boolean_fields:
                value = _boolean(row.get(field))
                if value is None:
                    reasons.append(f"missing:{field}")
                elif not value:
                    reasons.append(f"failed:{field}")
            trailing_return = _number(row.get("ret_252"))
            relative_volume = _number(row.get("relative_volume_50"))
            if trailing_return is None:
                reasons.append("missing:ret_252")
            if relative_volume is None:
                reasons.append("missing:relative_volume_50")
            if not reasons:
                eligible.append((instrument_id, trailing_return, relative_volume))
        eligibility[instrument_id] = {
            "eligible": not reasons,
            "reasons": tuple(reasons),
        }

    eligible.sort(key=lambda item: (-item[1], -item[2], item[0]))
    ranking = tuple(
        {
            "instrument_id": instrument_id,
            "ret_252": trailing_return,
            "relative_volume_50": relative_volume,
            "rank": index + 1,
        }
        for index, (instrument_id, trailing_return, relative_volume) in enumerate(eligible)
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
