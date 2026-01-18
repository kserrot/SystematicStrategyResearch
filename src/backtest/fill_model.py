from __future__ import annotations

from src.strategies.v1.spec import LimitOrder, ReasonCode, Side

Bar = dict[str, float]  # keys: "low", "high"


def place_limit_order(
    next_bar_ts: int,
    side: Side,
    limit_px: float,
    expiry_bars: int,
) -> LimitOrder:
    return LimitOrder(
        placed_ts=next_bar_ts,
        side=side,
        limit_px=float(limit_px),
        expiry_bars=int(expiry_bars),
        reasons=[ReasonCode.ORDER_PLACED],
    )


def check_fill(order: LimitOrder, bar_ts: int, bar: Bar) -> tuple[LimitOrder, bool]:
    if order.filled or order.expired:
        return order, False

    low = float(bar["low"])
    high = float(bar["high"])
    px = float(order.limit_px)

    if low <= px <= high:
        order.filled = True
        order.fill_ts = bar_ts
        order.fill_px = px
        order.reasons.append(ReasonCode.LIMIT_FILLED)
        return order, True

    return order, False


def step_age_and_expire(order: LimitOrder) -> tuple[LimitOrder, bool]:
    if order.filled or order.expired:
        return order, False

    order.age_bars += 1

    if order.age_bars >= order.expiry_bars:
        order.expired = True
        order.reasons.append(ReasonCode.LIMIT_EXPIRED)
        return order, True

    return order, False