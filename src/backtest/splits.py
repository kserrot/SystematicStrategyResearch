from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class ABCSplit:
    train: pd.DataFrame
    validate: pd.DataFrame
    test: pd.DataFrame


def make_abc_split_by_ts(
    df: pd.DataFrame,
    a_end_ts: int,
    b_end_ts: int,
    ts_col: str = "ts",
) -> ABCSplit:
    """
    Split into:
      A (train):    ts <= a_end_ts
      B (validate): a_end_ts < ts <= b_end_ts
      C (test):     ts > b_end_ts

    Assumes df has an integer timestamp column `ts_col`.
    """
    if ts_col not in df.columns:
        raise ValueError(f"df missing column: {ts_col}")

    d = df.sort_values(ts_col).reset_index(drop=True)

    train = d[d[ts_col] <= int(a_end_ts)].copy()
    validate = d[(d[ts_col] > int(a_end_ts)) & (d[ts_col] <= int(b_end_ts))].copy()
    test = d[d[ts_col] > int(b_end_ts)].copy()

    return ABCSplit(train=train, validate=validate, test=test)


def pick_cutoffs_by_ratio(
    df: pd.DataFrame,
    a_ratio: float = 0.6,
    b_ratio: float = 0.8,
    ts_col: str = "ts",
) -> tuple[int, int]:
    """
    Pick split cutoffs by rank in sorted timestamps.
    Defaults: 60% train, 20% validate, 20% test.
    Returns (a_end_ts, b_end_ts).
    """
    if not 0.0 < a_ratio < b_ratio < 1.0:
        raise ValueError("Require 0 < a_ratio < b_ratio < 1.")

    if ts_col not in df.columns:
        raise ValueError(f"df missing column: {ts_col}")

    d = df.sort_values(ts_col).reset_index(drop=True)
    n = len(d)
    if n < 3:
        raise ValueError("Need at least 3 rows to split.")

    a_idx = max(0, min(n - 2, int(round(a_ratio * (n - 1)))))
    b_idx = max(a_idx + 1, min(n - 1, int(round(b_ratio * (n - 1)))))

    a_end_ts = int(d.loc[a_idx, ts_col])
    b_end_ts = int(d.loc[b_idx, ts_col])
    return a_end_ts, b_end_ts
