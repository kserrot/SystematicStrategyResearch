import pandas as pd

from src.backtest.grid import run_grid_on_train


def test_grid_selects_best_by_total_net_pnl():
    # Same idea as the smoke: high only reaches 12.1.
    # With entry=10, atr=2, atr_mult=1:
    #   R = 2
    #   TP(r=1) = 12 -> hit
    #   TP(r=2) = 14 -> not hit
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
            {
                "ts": 180,
                "low": 10.0,
                "high": 12.1,
                "close": 12.0,
                "vwap": 10.0,
                "atr": 2.0,
                "ema50_1h": 101,
                "ema200_1h": 100,
            },
        ]
    )

    grid = [
        {
            "strategy": {
                "limit_expiry_bars": 3,
                "atr_stop_mult": 1.0,
                "take_profit_r": 1.0,
                "time_stop_bars": None,
                "maker_fee_bps": 0.0,
                "slippage_bps": 0.0,
            },
            "entry": {"min_vol_ratio": None},
        },
        {
            "strategy": {
                "limit_expiry_bars": 3,
                "atr_stop_mult": 1.0,
                "take_profit_r": 2.0,
                "time_stop_bars": None,
                "maker_fee_bps": 0.0,
                "slippage_bps": 0.0,
            },
            "entry": {"min_vol_ratio": None},
        },
    ]

    _, best = run_grid_on_train(train=df, symbol="X", grid=grid)
    assert best["strategy"]["take_profit_r"] == 1.0
