from __future__ import annotations

import pandas as pd

from src.backtest.splits import make_abc_split_by_ts


def test_abc_split_no_overlap() -> None:
    # tiny synthetic timeline
    ts = pd.date_range("2026-01-01", periods=10, freq="h", tz="UTC")
    df = pd.DataFrame(
        {
            "ts": (ts.astype("int64") // 1_000_000_000).astype(int),
            "open": 1.0,
            "high": 1.0,
            "low": 1.0,
            "close": 1.0,
        }
    )

    a_end = df["ts"].iloc[5]
    b_end = df["ts"].iloc[7]
    split = make_abc_split_by_ts(df, a_end_ts=a_end, b_end_ts=b_end)

    # ordering
    assert split.train["ts"].max() <= a_end
    assert split.validate["ts"].min() > a_end
    assert split.validate["ts"].max() <= b_end
    assert split.test["ts"].min() > b_end

    # no overlap
    assert set(split.train["ts"]).isdisjoint(set(split.validate["ts"]))
    assert set(split.train["ts"]).isdisjoint(set(split.test["ts"]))
    assert set(split.validate["ts"]).isdisjoint(set(split.test["ts"]))
