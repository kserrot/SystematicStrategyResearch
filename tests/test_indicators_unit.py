import numpy as np
import pandas as pd
import pytest

from src.features.core import atr, ema, rolling_vwap


def test_ema_matches_pandas_ewm_adjust_false() -> None:
    # Tiny deterministic series
    x = pd.Series([10.0, 11.0, 12.0, 11.0, 10.0], dtype="float64")

    # Implementation matches pandas ewm(adjust=False) but requires `span` samples
    # before producing a value (warmup / min_periods behavior).
    got = ema(x, span=3)
    exp = x.ewm(span=3, adjust=False, min_periods=3).mean()

    pd.testing.assert_series_equal(got, exp)


def test_atr_wilder_small_window_matches_manual() -> None:
    # Use a small window (3) so we can hand-check.
    high = pd.Series([10.0, 11.0, 12.0, 11.0, 13.0], dtype="float64")
    low = pd.Series([9.0, 10.0, 10.0, 10.0, 11.0], dtype="float64")
    close = pd.Series([9.5, 10.5, 11.0, 10.5, 12.0], dtype="float64")

    window = 3

    # True range sequence (manual):
    # TR0 = high0-low0
    # TRt = max(high-low, abs(high-prev_close), abs(low-prev_close))
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    # Wilder smoothing in this codebase is implemented as EMA(TR) with alpha=1/window
    # and a warmup of `window` samples.
    exp = tr.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()

    got = atr(high, low, close, window=window)

    pd.testing.assert_series_equal(got, exp)

    # Sanity: first `window-1` values should be NaN
    assert np.isnan(got.iloc[0])
    assert np.isnan(got.iloc[1])

    # Spot-check a couple values to make failures easier to read
    assert got.iloc[2] == pytest.approx(exp.iloc[2])
    assert got.iloc[4] == pytest.approx(exp.iloc[4])


def test_rolling_vwap_matches_manual_typical_price_volume() -> None:
    # Typical price = (h + l + c) / 3
    df = pd.DataFrame(
        {
            "high": [10.0, 12.0, 11.0, 13.0],
            "low": [9.0, 11.0, 10.0, 12.0],
            "close": [9.5, 11.5, 10.5, 12.5],
            "volume": [100.0, 200.0, 100.0, 100.0],
        }
    )

    window = 2
    got = rolling_vwap(df, window=window)

    tp = (df["high"] + df["low"] + df["close"]) / 3.0
    num = (tp * df["volume"]).rolling(window).sum()
    den = df["volume"].rolling(window).sum()
    exp = num / den

    pd.testing.assert_series_equal(got, exp, check_names=False)
