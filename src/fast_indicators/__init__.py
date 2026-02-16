from __future__ import annotations

from importlib import import_module
from typing import Any

import numpy as np


def _try_import_cpp() -> Any | None:
    try:
        return import_module("_fast_indicators")
    except Exception:
        return None


_cpp = _try_import_cpp()


def ema(x: np.ndarray, span: int) -> np.ndarray:
    """
    EMA wrapper.

    Tries the C++ extension first (fast_indicators.ema).
    Falls back to a small pure-Python/Numpy implementation if unavailable.
    """
    x_arr = np.asarray(x, dtype=np.float64)

    if _cpp is not None:
        return _cpp.ema(x_arr, int(span))

    if span <= 0:
        raise ValueError("span must be > 0")
    if x_arr.ndim != 1:
        raise ValueError("x must be a 1D array")

    if x_arr.size == 0:
        return x_arr.copy()

    alpha = 2.0 / (float(span) + 1.0)
    out = np.empty_like(x_arr)
    out[0] = x_arr[0]
    for i in range(1, x_arr.size):
        out[i] = alpha * x_arr[i] + (1.0 - alpha) * out[i - 1]
    return out
