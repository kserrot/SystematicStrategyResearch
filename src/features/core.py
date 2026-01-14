from __future__ import annotations

import numpy as np
import pandas as pd


def _require_cols(df: pd.DataFrame, cols: list[str]) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def prepare_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """
    Expected columns: ts, open, high, low, close, volume
    Returns a copy sorted by ts with numeric columns coerced.
    """
    _require_cols(df, ["ts", "open", "high", "low", "close", "volume"])

    out = df.copy()
    out["ts"] = pd.to_datetime(out["ts"], utc=True, errors="coerce")
    out = out.sort_values("ts").reset_index(drop=True)

    for c in ["open", "high", "low", "close", "volume"]:
        out[c] = pd.to_numeric(out[c], errors="coerce")

    return out


def log_return(close: pd.Series) -> pd.Series:
    # log return
    return np.log(close).diff()


def sma(x: pd.Series, window: int) -> pd.Series:
    # rolling mean
    return x.rolling(window=window, min_periods=window).mean()


def ema(x: pd.Series, span: int) -> pd.Series:
    # exp mean
    return x.ewm(span=span, adjust=False, min_periods=span).mean()


def rolling_vol(x: pd.Series, window: int) -> pd.Series:
    # rolling std
    return x.rolling(window=window, min_periods=window).std()


def rsi(close: pd.Series, window: int = 14) -> pd.Series:
    """
    Wilder RSI (causal).
    """
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)

    # Wilder smoothing (EMA with alpha=1/window)
    avg_gain = gain.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()

    rs = avg_gain / avg_loss
    out = 100.0 - (100.0 / (1.0 + rs))

    return out


def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    # TR parts
    prev_close = close.shift(1)
    tr1 = (high - low).abs()
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()

    return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)


def atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
    """
    Wilder ATR (causal).
    """
    tr = true_range(high, low, close)
    return tr.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()


def rolling_vwap(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """
    Approx VWAP from OHLCV bars using typical price * volume rolling sums.
    """
    _require_cols(df, ["high", "low", "close", "volume"])
    tp = (df["high"] + df["low"] + df["close"]) / 3.0
    pv = tp * df["volume"]
    pv_sum = pv.rolling(window=window, min_periods=window).sum()
    v_sum = df["volume"].rolling(window=window, min_periods=window).sum()
    return pv_sum / v_sum


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds core features to a prepared OHLCV dataframe.
    Output columns are prefixed with feature__ for clarity.
    """
    x = prepare_ohlcv(df)

    x["feature__ret_1"] = log_return(x["close"])
    x["feature__vol_20"] = rolling_vol(x["feature__ret_1"], 20)

    x["feature__sma_20"] = sma(x["close"], 20)
    x["feature__ema_20"] = ema(x["close"], 20)

    x["feature__rsi_14"] = rsi(x["close"], 14)
    x["feature__atr_14"] = atr(x["high"], x["low"], x["close"], 14)

    x["feature__vwap_20"] = rolling_vwap(x, 20)
    x["feature__vwap_dist_20"] = (x["close"] - x["feature__vwap_20"]) / x["close"]

    return x
