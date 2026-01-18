import pytest

from src.strategies.v1.exits import check_long_exit, compute_long_brackets
from src.strategies.v1.spec import ReasonCode


def test_compute_brackets_basic():
    b = compute_long_brackets(entry_px=100.0, atr=2.0, atr_mult=1.0, take_profit_r=2.0)
    # stop = 98, R=2, tp = 104
    assert b.stop_px == 98.0
    assert b.tp_px == 104.0


def test_exit_stop_hit():
    b = compute_long_brackets(entry_px=100.0, atr=2.0, atr_mult=1.0, take_profit_r=2.0)
    exit_px, reason = check_long_exit(low=97.5, high=103.0, brackets=b)
    assert exit_px == 98.0
    assert reason == ReasonCode.STOP


def test_exit_tp_hit():
    b = compute_long_brackets(entry_px=100.0, atr=2.0, atr_mult=1.0, take_profit_r=2.0)
    exit_px, reason = check_long_exit(low=99.0, high=104.5, brackets=b)
    assert exit_px == 104.0
    assert reason == ReasonCode.TAKE_PROFIT


def test_exit_both_hit_same_bar_is_stop_first():
    b = compute_long_brackets(entry_px=100.0, atr=2.0, atr_mult=1.0, take_profit_r=2.0)
    # low crosses stop and high crosses TP in same candle -> STOP (worst case)
    exit_px, reason = check_long_exit(low=97.0, high=105.0, brackets=b)
    assert exit_px == 98.0
    assert reason == ReasonCode.STOP


def test_atr_must_be_positive():
    with pytest.raises(ValueError):
        compute_long_brackets(entry_px=100.0, atr=0.0, atr_mult=1.0, take_profit_r=2.0)
