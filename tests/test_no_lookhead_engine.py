import pandas as pd
import pytest

from src.backtest.engine import run_backtest_v1
from src.strategies.v1.entry import EntryRuleParams
from src.strategies.v1.spec import StrategyParams


def test_limit_is_placed_next_bar_not_same_bar():
    """
    If the engine incorrectly places the limit on the SAME bar as the cross,
    it would fill on that bar. Our engine must place on the NEXT bar, so it
    should NOT fill here and produce 0 trades.
    """
    df = pd.DataFrame(
        [
            # i=0 (prev)
            {
                "ts": 0,
                "low": 9.8,
                "high": 10.2,
                "close": 9.9,
                "vwap": 10.0,
                "atr": 2.0,
                "ema50_1h": 101,
                "ema200_1h": 100,
            },
            # i=1 cross above vwap happens here
            # vwap=10.0 would fill if order was placed SAME bar (low<=10<=high)
            {
                "ts": 60,
                "low": 9.9,
                "high": 10.3,
                "close": 10.2,
                "vwap": 10.0,
                "atr": 2.0,
                "ema50_1h": 101,
                "ema200_1h": 100,
            },
            # i=2 next bar DOES NOT contain limit price 10.0 -> no fill
            {
                "ts": 120,
                "low": 10.6,
                "high": 10.9,
                "close": 10.8,
                "vwap": 10.0,
                "atr": 2.0,
                "ema50_1h": 101,
                "ema200_1h": 100,
            },
            # i=3 nothing
            {
                "ts": 180,
                "low": 10.7,
                "high": 11.0,
                "close": 10.9,
                "vwap": 10.0,
                "atr": 2.0,
                "ema50_1h": 101,
                "ema200_1h": 100,
            },
        ]
    )

    params = StrategyParams(
        limit_expiry_bars=2,
        atr_stop_mult=1.0,
        take_profit_r=2.0,
        time_stop_bars=1,
        maker_fee_bps=0.0,
        slippage_bps=0.0,
    )

    trades = run_backtest_v1(
        df,
        symbol="NLH",
        params=params,
        entry_params=EntryRuleParams(min_vol_ratio=None),
    )

    assert trades == []


def test_engine_uses_atr_from_fill_bar_not_future_bar():
    """
    ATR must be taken from the fill bar. We set ATR=0 on the fill bar (invalid),
    but ATR>0 on the next bar. If the engine incorrectly uses the next bar's ATR,
    it would not raise.
    """
    df = pd.DataFrame(
        [
            {
                "ts": 0,
                "low": 9.8,
                "high": 10.2,
                "close": 9.9,
                "vwap": 10.0,
                "atr": 2.0,
                "ema50_1h": 101,
                "ema200_1h": 100,
            },
            # cross bar
            {
                "ts": 60,
                "low": 9.9,
                "high": 10.3,
                "close": 10.2,
                "vwap": 10.0,
                "atr": 2.0,
                "ema50_1h": 101,
                "ema200_1h": 100,
            },
            # fill bar: limit=10.0 fills, but ATR=0 should raise ValueError
            {
                "ts": 120,
                "low": 9.95,
                "high": 10.05,
                "close": 10.0,
                "vwap": 10.0,
                "atr": 0.0,
                "ema50_1h": 101,
                "ema200_1h": 100,
            },
            # next bar (future): ATR is valid here, but engine must not use it
            {
                "ts": 180,
                "low": 9.9,
                "high": 10.2,
                "close": 10.1,
                "vwap": 10.0,
                "atr": 2.0,
                "ema50_1h": 101,
                "ema200_1h": 100,
            },
        ]
    )

    params = StrategyParams(
        limit_expiry_bars=3,
        atr_stop_mult=1.0,
        take_profit_r=2.0,
        time_stop_bars=None,
        maker_fee_bps=0.0,
        slippage_bps=0.0,
    )

    with pytest.raises(ValueError):
        run_backtest_v1(
            df,
            symbol="ATR_FILL",
            params=params,
            entry_params=EntryRuleParams(min_vol_ratio=None),
        )
        