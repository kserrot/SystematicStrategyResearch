from src.backtest.fill_model import check_fill, place_limit_order, step_age_and_expire
from src.strategies.v1.spec import ReasonCode, Side


def test_limit_fills_when_inside_range():
    order = place_limit_order(next_bar_ts=100, side=Side.LONG, limit_px=10.0, expiry_bars=4)
    bar = {"low": 9.5, "high": 10.5}

    order, filled = check_fill(order, bar_ts=110, bar=bar)

    assert filled is True
    assert order.filled is True
    assert order.fill_ts == 110
    assert order.fill_px == 10.0
    assert ReasonCode.LIMIT_FILLED in order.reasons


def test_limit_does_not_fill_when_outside_range():
    order = place_limit_order(next_bar_ts=100, side=Side.LONG, limit_px=10.0, expiry_bars=4)
    bar = {"low": 10.1, "high": 11.0}

    order, filled = check_fill(order, bar_ts=110, bar=bar)

    assert filled is False
    assert order.filled is False
    assert order.fill_ts is None
    assert order.fill_px is None


def test_limit_expires_after_n_bars():
    order = place_limit_order(next_bar_ts=100, side=Side.LONG, limit_px=10.0, expiry_bars=3)

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