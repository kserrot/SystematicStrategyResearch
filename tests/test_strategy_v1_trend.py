from src.strategies.v1.spec import ReasonCode
from src.strategies.v1.trend_filter import trend_ok


def test_trend_ok_when_ema50_above_ema200():
    res = trend_ok(ema50_1h=101.0, ema200_1h=100.0)
    assert res.ok is True
    assert res.reason is None


def test_trend_fail_when_ema50_not_above_ema200():
    res = trend_ok(ema50_1h=100.0, ema200_1h=100.0)
    assert res.ok is False
    assert res.reason == ReasonCode.TREND_FAIL