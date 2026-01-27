from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


@dataclass(frozen=True)
class ReportPaths:
    equity_csv: Path
    equity_png: Path
    drawdown_png: Path


def build_equity_curve(trades_csv: Path) -> pd.DataFrame:
    """
    Reads trades.csv and returns a dataframe with:
      trade_idx, entry_ts, exit_ts, net_pnl, equity, drawdown
    """
    df = pd.read_csv(trades_csv)

    if "net_pnl" not in df.columns:
        raise ValueError("trades.csv missing column: net_pnl")

    df = df.copy()
    df["trade_idx"] = range(1, len(df) + 1)

    if "entry_ts" not in df.columns:
        df["entry_ts"] = pd.NA
    if "exit_ts" not in df.columns:
        df["exit_ts"] = pd.NA

    df["net_pnl"] = df["net_pnl"].astype(float)
    df["equity"] = df["net_pnl"].cumsum()

    running_max = df["equity"].cummax()
    df["drawdown"] = df["equity"] - running_max

    cols = ["trade_idx", "entry_ts", "exit_ts", "net_pnl", "equity", "drawdown"]
    return df[cols]


def save_report(
    eq: pd.DataFrame,
    out_dir: Path,
    prefix: str = "",
) -> ReportPaths:
    out_dir.mkdir(parents=True, exist_ok=True)

    pfx = f"{prefix}_" if prefix else ""

    equity_csv = out_dir / f"{pfx}equity.csv"
    equity_png = out_dir / f"{pfx}equity_curve.png"
    drawdown_png = out_dir / f"{pfx}drawdown.png"

    eq.to_csv(equity_csv, index=False)

    # Equity plot
    plt.figure()
    plt.plot(eq["trade_idx"], eq["equity"], marker="o", linewidth=1)
    plt.xlabel("Trade #")
    plt.ylabel("Equity (cum net pnl)")
    plt.title("Equity Curve")
    plt.tight_layout()
    plt.savefig(equity_png, dpi=150)
    plt.close()

    # Drawdown plot
    plt.figure()
    plt.plot(eq["trade_idx"], eq["drawdown"], marker="o", linewidth=1)
    plt.axhline(0, linewidth=1)
    plt.xlabel("Trade #")
    plt.ylabel("Drawdown")
    plt.title("Drawdown")
    plt.tight_layout()
    plt.savefig(drawdown_png, dpi=150)
    plt.close()

    return ReportPaths(
        equity_csv=equity_csv,
        equity_png=equity_png,
        drawdown_png=drawdown_png,
    )
