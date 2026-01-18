import pandas as pd

from src.backtest.engine import run_backtest_v1
from src.strategies.v1.entry import EntryRuleParams
from src.strategies.v1.spec import ReasonCode, Side, StrategyParams


def test_engine_generates_one_trade_with_take_profit():
    # ATR=2, atr_mult=1 => stop = entry-2, R=2, TP = entry+4
    # Entry fills at 10.0 => TP = 14.0 (we'll hit it with high)
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
            # fill bar: limit=10.0 fills
            {
                "ts": 120,
                "low": 9.95,
                "high": 10.05,
                "close": 10.01,
                "vwap": 10.0,
                "atr": 2.0,
                "ema50_1h": 101,
                "ema200_1h": 100,
            },
            # exit bar: high hits TP=14.0
            {
                "ts": 180,
                "low": 10.0,
                "high": 14.1,
                "close": 14.0,
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
    )

    trades = run_backtest_v1(
        df,
        symbol="TEST",
        params=params,
        entry_params=EntryRuleParams(min_vol_ratio=None),
    )

    assert len(trades) == 1
    t = trades[0]
    assert t.symbol == "TEST"
    assert t.side == Side.LONG
    assert t.entry_px == 10.0
    assert t.exit_px == 14.0
    assert ReasonCode.TAKE_PROFIT in t.reasons