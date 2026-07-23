"""Deterministic selection by classic twelve-minus-one-month momentum."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class SelectionResult:
    as_of: str
    eligibility: dict[str, dict[str, Any]]
    ranking: tuple[dict[str, Any], ...]
    targets: tuple[dict[str, Any], ...]
    fallback_used: bool


def _number(value: Any) -> float | None:
    try:
        result = None if value in (None, "") else float(value)
    except (TypeError, ValueError):
        return None
    return result if result is not None and math.isfinite(result) else None


def select(
    *,
    as_of: str,
    candidates: Sequence[str],
    features: Mapping[str, Mapping[str, Any]],
    target_count: int = 10,
    fallback_mode: str = "empty",
    fallback_ticker: str | None = None,
) -> SelectionResult:
    """Rank finite point-in-time ``ret_252_21`` features."""
    if target_count < 1:
        raise ValueError("target_count must be positive")
    if fallback_mode not in {"empty", "fallback"}:
        raise ValueError("fallback_mode must be 'empty' or 'fallback'")
    if fallback_mode == "fallback" and not fallback_ticker:
        raise ValueError("fallback_ticker is required in fallback mode")

    eligibility: dict[str, dict[str, Any]] = {}
    eligible: list[tuple[str, float]] = []
    for instrument_id in candidates:
        row = features.get(instrument_id)
        reasons: list[str] = []
        if row is None:
            reasons.append("missing:feature_row")
        else:
            value = _number(row.get("ret_252_21"))
            if value is None:
                reasons.append("missing_or_non_finite:ret_252_21")
            else:
                eligible.append((instrument_id, value))
        eligibility[instrument_id] = {
            "eligible": not reasons,
            "reasons": tuple(reasons),
        }

    ascending = sorted(eligible, key=lambda item: (item[1], item[0]))
    count = len(ascending)
    percentiles = {
        ticker: (position / (count - 1) if count > 1 else 1.0)
        for position, (ticker, _) in enumerate(ascending)
    }
    ordered = sorted(eligible, key=lambda item: (-item[1], item[0]))
    ranking = tuple(
        {
            "instrument_id": ticker,
            "ret_252_21": value,
            "momentum_percentile": percentiles[ticker],
            "rating": round(100 * percentiles[ticker]),
            "rank": position + 1,
        }
        for position, (ticker, value) in enumerate(ordered)
    )
    selected = ranking[:target_count]
    fallback_used = not selected and fallback_mode == "fallback"
    if fallback_used:
        targets = ({"instrument_id": fallback_ticker, "weight": 1.0},)
    else:
        weight = 1.0 / len(selected) if selected else 0.0
        targets = tuple(
            {"instrument_id": row["instrument_id"], "weight": weight}
            for row in selected
        )
    return SelectionResult(as_of, eligibility, ranking, targets, fallback_used)
