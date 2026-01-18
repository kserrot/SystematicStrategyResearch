from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np


@dataclass(frozen=True)
class Metrics:
    trades: int
    win_rate: float
    expectancy: float
    profit_factor: float
    mdd: float
    total_net_pnl: float


def compute_metrics(net_pnls: list[float]) -> Metrics:
    arr = np.array([float(x) for x in net_pnls], dtype=float)

    n = int(arr.size)
    if n == 0:
        return Metrics(
            trades=0,
            win_rate=0.0,
            expectancy=0.0,
            profit_factor=0.0,
            mdd=0.0,
            total_net_pnl=0.0,
        )

    wins = arr[arr > 0]
    losses = arr[arr < 0]

    win_rate = float(wins.size) / float(n)
    expectancy = float(arr.mean())
    total_net = float(arr.sum())

    win_sum = float(wins.sum()) if wins.size else 0.0
    loss_sum = float(losses.sum()) if losses.size else 0.0  # negative

    profit_factor = win_sum / abs(loss_sum) if loss_sum != 0.0 else float("inf")

    equity = np.cumsum(arr)
    run_max = np.maximum.accumulate(equity) if n else equity
    drawdown = equity - run_max
    mdd = float(drawdown.min()) if n else 0.0  # negative number (e.g., -3.2)

    return Metrics(
        trades=n,
        win_rate=win_rate,
        expectancy=expectancy,
        profit_factor=profit_factor,
        mdd=mdd,
        total_net_pnl=total_net,
    )


def metrics_to_dict(m: Metrics) -> dict:
    d = asdict(m)
    # Normalize inf for JSON
    if d["profit_factor"] == float("inf"):
        d["profit_factor"] = None
        d["profit_factor_note"] = "infinite (no losing trades)"
    return d