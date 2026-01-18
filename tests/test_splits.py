import pandas as pd

from src.backtest.splits import make_abc_split_by_ts


def test_make_abc_split_by_ts_non_overlapping():
    df = pd.DataFrame([{"ts": t} for t in [1, 2, 3, 4, 5, 6]])
    split = make_abc_split_by_ts(df, a_end_ts=2, b_end_ts=4)

    assert split.train["ts"].max() == 2
    assert split.validate["ts"].min() == 3
    assert split.validate["ts"].max() == 4
    assert split.test["ts"].min() == 5