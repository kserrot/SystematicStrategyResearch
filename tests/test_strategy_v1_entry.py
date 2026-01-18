from src.strategies.v1.entry import EntryRuleParams, build_entry_signal
from src.strategies.v1.spec import ReasonCode, Side


def test_entry_signal_on_cross_above_vwap():
    sig = build_entry_signal(
        ts=100,
        prev_close=9.9,
        prev_vwap=10.0,
        close=10.1,
        vwap=10.0,
        side=Side.LONG,
        vol_ratio=None,
        params=EntryRuleParams(min_vol_ratio=None),
    )
    assert sig is not None
    assert sig.side == Side.LONG
    assert sig.limit_px == 10.0
    assert ReasonCode.ENTRY_CROSS in sig.reasons


def test_entry_signal_requires_vol_confirm_when_enabled():
    # Cross occurs, but vol_ratio too low => no signal
    sig = build_entry_signal(
        ts=100,
        prev_close=9.9,
        prev_vwap=10.0,
        close=10.1,
        vwap=10.0,
        side=Side.LONG,
        vol_ratio=1.1,
        params=EntryRuleParams(min_vol_ratio=1.5),
    )
    assert sig is None


def test_entry_signal_passes_when_vol_confirm_met():
    sig = build_entry_signal(
        ts=100,
        prev_close=9.9,
        prev_vwap=10.0,
        close=10.1,
        vwap=10.0,
        side=Side.LONG,
        vol_ratio=2.0,
        params=EntryRuleParams(min_vol_ratio=1.5),
    )
    assert sig is not None
    assert ReasonCode.VOL_CONFIRM in sig.reasons