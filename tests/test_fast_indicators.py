from __future__ import annotations

import numpy as np

from src.fast_indicators import ema


def ema_py(x: np.ndarray, span: int) -> np.ndarray:
    x = np.asarray(x, dtype=np.float64)
    alpha = 2.0 / (float(span) + 1.0)
    out = np.empty_like(x)
    out[0] = x[0]
    for i in range(1, x.size):
        out[i] = alpha * x[i] + (1.0 - alpha) * out[i - 1]
    return out


def test_ema_known_values() -> None:
    x = np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float64)
    out = ema(x, 3)

    # alpha = 0.5
    # [1.0, 1.5, 2.25, 3.125]
    expected = np.array([1.0, 1.5, 2.25, 3.125], dtype=np.float64)
    assert np.allclose(out, expected, rtol=0.0, atol=0.0)


def test_ema_matches_python_reference() -> None:
    rng = np.random.default_rng(7)
    x = rng.normal(size=200).astype(np.float64)

    out = ema(x, 20)
    expected = ema_py(x, 20)

    assert np.allclose(out, expected, rtol=1e-12, atol=1e-12)


def test_ema_empty() -> None:
    x = np.array([], dtype=np.float64)
    out = ema(x, 10)
    assert out.size == 0
