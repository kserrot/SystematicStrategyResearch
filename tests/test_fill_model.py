from src.backtest.fill_model import check_fill, place_limit_order, step_age_and_expire
from src.strategies.v1.spec import ReasonCode, Side


def test_limit_fills_when_inside_range():
    order = place_limit_order(
        next_bar_ts=100,
        side=Side.LONG,
        limit_px=10.0,
        expiry_bars=4,
    )
    bar = {"low": 9.5, "high": 10.5}

    order, filled = check_fill(order, bar_ts=110, bar=bar)

    assert filled is True
    assert order.filled is True
    assert order.fill_ts == 110
    assert order.fill_px == 10.0
    assert ReasonCode.LIMIT_FILLED in order.reasons


def test_limit_does_not_fill_when_outside_range():
    order = place_limit_order(
        next_bar_ts=100,
        side=Side.LONG,
        limit_px=10.0,
        expiry_bars=4,
    )
    bar = {"low": 10.1, "high": 11.0}

    order, filled = check_fill(order, bar_ts=110, bar=bar)

    assert filled is False
    assert order.filled is False
    assert order.fill_ts is None
    assert order.fill_px is None


def test_limit_fills_on_second_bar_within_expiry():
    order = place_limit_order(
        next_bar_ts=100,
        side=Side.LONG,
        limit_px=10.0,
        expiry_bars=3,
    )

    # Bar 1: does not fill
    bar1 = {"low": 10.1, "high": 11.0}
    order, filled = check_fill(order, bar_ts=110, bar=bar1)
    assert filled is False
    assert order.filled is False

    # Engine ages orders once per bar
    order, expired = step_age_and_expire(order)
    assert expired is False
    assert order.age_bars == 1

    # Bar 2: now price trades through the limit -> fills
    bar2 = {"low": 9.5, "high": 10.5}
    order, filled = check_fill(order, bar_ts=120, bar=bar2)

    assert filled is True
    assert order.filled is True
    assert order.expired is False
    assert order.fill_ts == 120
    assert order.fill_px == 10.0
    assert ReasonCode.LIMIT_FILLED in order.reasons
    assert ReasonCode.LIMIT_EXPIRED not in order.reasons


def test_limit_does_not_fill_then_expires_with_engine_like_loop():
    order = place_limit_order(
        next_bar_ts=100,
        side=Side.LONG,
        limit_px=10.0,
        expiry_bars=3,
    )

    bars = [
        (110, {"low": 10.1, "high": 11.0}),
        (120, {"low": 10.2, "high": 11.2}),
        (130, {"low": 10.3, "high": 11.3}),
    ]

    for ts, bar in bars:
        order, filled = check_fill(order, bar_ts=ts, bar=bar)
        assert filled is False
        order, _expired = step_age_and_expire(order)

    assert order.filled is False
    assert order.fill_ts is None
    assert order.fill_px is None
    assert order.expired is True
    assert ReasonCode.LIMIT_EXPIRED in order.reasons


def test_check_fill_is_idempotent_when_already_filled_or_expired():
    bar = {"low": 9.5, "high": 10.5}

    # Filled order: subsequent calls should not change state
    order = place_limit_order(
        next_bar_ts=100,
        side=Side.LONG,
        limit_px=10.0,
        expiry_bars=3,
    )
    order, filled = check_fill(order, bar_ts=110, bar=bar)
    assert filled is True

    fill_ts = order.fill_ts
    fill_px = order.fill_px
    reasons = list(order.reasons)

    order, filled_again = check_fill(order, bar_ts=120, bar=bar)
    assert filled_again is False
    assert order.fill_ts == fill_ts
    assert order.fill_px == fill_px
    assert order.reasons == reasons

    # Expired order: subsequent calls should not change state
    order2 = place_limit_order(
        next_bar_ts=100,
        side=Side.LONG,
        limit_px=10.0,
        expiry_bars=1,
    )
    order2, expired = step_age_and_expire(order2)
    assert expired is True
    assert order2.expired is True

    fill_ts2 = order2.fill_ts
    fill_px2 = order2.fill_px
    reasons2 = list(order2.reasons)

    order2, filled2 = check_fill(order2, bar_ts=110, bar=bar)
    assert filled2 is False
    assert order2.fill_ts == fill_ts2
    assert order2.fill_px == fill_px2
    assert order2.reasons == reasons2


def test_limit_expires_after_n_bars():
    order = place_limit_order(
        next_bar_ts=100,
        side=Side.LONG,
        limit_px=10.0,
        expiry_bars=3,
    )

    order, expired = step_age_and_expire(order)
    assert expired is False
    assert order.age_bars == 1

    order, expired = step_age_and_expire(order)
    assert expired is False
    assert order.age_bars == 2

    order, expired = step_age_and_expire(order)
    assert expired is True
    assert order.expired is True
    assert ReasonCode.LIMIT_EXPIRED in order.reasons
