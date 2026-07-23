"""Pure transition function for the partial-profit/breakeven/time-exit policy."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


INITIAL_STOP_RETURN = 0.075
PARTIAL_PROFIT_RETURN = 0.225
PARTIAL_SALE_FRACTION = 0.50
STAGNATION_SESSIONS = 15
MAXIMUM_HOLDING_SESSIONS = 378
_EPSILON = 1e-12


@dataclass(frozen=True)
class PolicyResult:
    as_of: str
    orders: tuple[dict[str, Any], ...]
    retained_positions: tuple[dict[str, Any], ...]
    unallocated_cash: dict[str, Any]
    constraint_events: tuple[dict[str, Any], ...]


def transition(
    *,
    as_of: str,
    selection_intent: Sequence[Mapping[str, Any]],
    portfolio_state: Sequence[Mapping[str, Any]],
    cash_state: Mapping[str, Any],
    daily_market_state: Mapping[str, Mapping[str, Any]],
    session_index: Mapping[str, int],
) -> PolicyResult:
    """Return this session's deterministic order intents without mutating input.

    ``portfolio_state`` contains one record per open lot. A lot must supply
    ``instrument_id``, ``entry_price``, ``original_quantity``, and
    ``remaining_quantity``. ``partial_profit_filled`` defaults to false.
    ``session_index`` maps instrument IDs to completed post-entry sessions.
    """
    orders: list[dict[str, Any]] = []
    retained: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    held = set()

    for lot in portfolio_state:
        instrument_id = str(lot.get("instrument_id", ""))
        if instrument_id:
            held.add(instrument_id)
        values = _valid_lot(lot)
        if not instrument_id or values is None:
            events.append(_event(instrument_id, "invalid_lot_state"))
            continue
        entry_price, original_quantity, remaining_quantity = values
        sessions = session_index.get(instrument_id)
        if not isinstance(sessions, int) or sessions < 0:
            events.append(_event(instrument_id, "invalid_session_index"))
            retained.append(_retained(instrument_id, "invalid_session_index"))
            continue

        if sessions >= MAXIMUM_HOLDING_SESSIONS:
            orders.append(_sell(instrument_id, remaining_quantity, "market", "maximum_holding_exit"))
            continue

        bar = daily_market_state.get(instrument_id)
        parsed_bar = _bar(bar)
        if parsed_bar is None:
            events.append(_event(instrument_id, "missing_daily_bar"))
            retained.append(_retained(instrument_id, "missing_daily_bar"))
            continue
        open_price, high, low, close = parsed_bar
        partial_filled = bool(lot.get("partial_profit_filled", False))
        stop_price = entry_price if partial_filled else entry_price * (1.0 - INITIAL_STOP_RETURN)
        target_price = entry_price * (1.0 + PARTIAL_PROFIT_RETURN)
        stop_hit = low <= stop_price
        target_hit = not partial_filled and high >= target_price

        if stop_hit:
            if target_hit:
                events.append(_event(instrument_id, "ambiguous_bar_stop_first"))
            orders.append(
                _sell(
                    instrument_id,
                    remaining_quantity,
                    "stop",
                    "breakeven_stop" if partial_filled else "initial_stop",
                    stop_price=stop_price,
                    expected_fill_price=min(open_price, stop_price),
                )
            )
            continue

        if target_hit:
            quantity = min(remaining_quantity, original_quantity * PARTIAL_SALE_FRACTION)
            orders.append(
                _sell(
                    instrument_id,
                    quantity,
                    "limit",
                    "partial_profit",
                    limit_price=target_price,
                    expected_fill_price=max(open_price, target_price),
                )
            )
            retained.append(_retained(instrument_id, "partial_profit_remainder"))
            continue

        if sessions >= STAGNATION_SESSIONS and close <= entry_price:
            orders.append(_sell(instrument_id, remaining_quantity, "market", "stagnation_exit"))
            continue

        orders.append(
            _sell(
                instrument_id,
                remaining_quantity,
                "stop",
                "breakeven_stop" if partial_filled else "initial_stop",
                stop_price=stop_price,
            )
        )
        if not partial_filled:
            orders.append(
                _sell(
                    instrument_id,
                    min(remaining_quantity, original_quantity * PARTIAL_SALE_FRACTION),
                    "limit",
                    "partial_profit",
                    limit_price=target_price,
                )
            )
        retained.append(_retained(instrument_id, "exit_orders_active"))

    settled_cash = _positive_number(cash_state.get("settled"))
    valid_targets = _targets(selection_intent, events)
    if settled_cash is None:
        events.append(_event("", "invalid_settled_cash"))
        settled_cash = 0.0
    for instrument_id, weight in valid_targets:
        if instrument_id in held:
            continue
        orders.append(
            {
                "instrument_id": instrument_id,
                "side": "buy",
                "order_type": "target_notional",
                "reason": "selection_entry",
                "target_weight": weight,
                "notional": settled_cash * weight,
            }
        )

    allocated = sum(
        float(order["notional"])
        for order in orders
        if order["side"] == "buy" and order["order_type"] == "target_notional"
    )
    unallocated = max(0.0, settled_cash - allocated)
    reason = "reserved_for_existing_positions" if held else "not_selected"
    if allocated and unallocated <= _EPSILON:
        reason = "fully_allocated"
    return PolicyResult(
        as_of=as_of,
        orders=tuple(orders),
        retained_positions=tuple(retained),
        unallocated_cash={"amount": unallocated, "reason": reason},
        constraint_events=tuple(events),
    )


def _targets(
    selection_intent: Sequence[Mapping[str, Any]],
    events: list[dict[str, Any]],
) -> list[tuple[str, float]]:
    targets: list[tuple[str, float]] = []
    seen = set()
    total = 0.0
    for target in selection_intent:
        instrument_id = str(target.get("instrument_id", ""))
        weight = _positive_number(target.get("weight"))
        if not instrument_id or weight is None or instrument_id in seen:
            events.append(_event(instrument_id, "invalid_selection_target"))
            continue
        seen.add(instrument_id)
        total += weight
        targets.append((instrument_id, weight))
    if total > 1.0 + _EPSILON:
        events.append(_event("", "target_weights_exceed_one"))
        return []
    return targets


def _valid_lot(lot: Mapping[str, Any]) -> tuple[float, float, float] | None:
    entry = _positive_number(lot.get("entry_price"))
    original = _positive_number(lot.get("original_quantity"))
    remaining = _positive_number(lot.get("remaining_quantity"))
    if entry is None or original is None or remaining is None or remaining > original + _EPSILON:
        return None
    return entry, original, remaining


def _bar(bar: Mapping[str, Any] | None) -> tuple[float, float, float, float] | None:
    if not bar:
        return None
    values = tuple(_positive_number(bar.get(name)) for name in ("open", "high", "low", "close"))
    if any(value is None for value in values):
        return None
    open_price, high, low, close = values
    if low > high:
        return None
    return open_price, high, low, close


def _positive_number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _sell(
    instrument_id: str,
    quantity: float,
    order_type: str,
    reason: str,
    **fields: float,
) -> dict[str, Any]:
    return {
        "instrument_id": instrument_id,
        "side": "sell",
        "quantity": quantity,
        "order_type": order_type,
        "reason": reason,
        **fields,
    }


def _retained(instrument_id: str, reason: str) -> dict[str, Any]:
    return {"instrument_id": instrument_id, "reason": reason}


def _event(instrument_id: str, reason: str) -> dict[str, Any]:
    return {"instrument_id": instrument_id, "reason": reason}
