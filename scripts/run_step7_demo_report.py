from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.reports.generate import generate_report_from_trades


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Step 7: generate a deterministic demo report.")
    p.add_argument(
        "--out-dir",
        type=Path,
        default=Path("reports/sample_demo"),
        help="Output folder for demo report artifacts.",
    )
    p.add_argument(
        "--n-trades",
        type=int,
        default=30,
        help="How many demo trades to generate.",
    )
    return p.parse_args()


def _make_demo_trades_csv(path: Path, n_trades: int) -> None:
    """
    Creates a deterministic trades.csv with wins + losses so equity/drawdown lines show.
    Columns match what Step 7 expects: entry_ts, exit_ts, net_pnl
    """
    rows = []
    entry = 0
    for i in range(1, n_trades + 1):
        # Deterministic pattern: small win streaks + occasional losses
        if i % 7 == 0:
            pnl = -3.0
        elif i % 11 == 0:
            pnl = -2.0
        else:
            pnl = 1.0

        rows.append(
            {
                "entry_ts": entry,
                "exit_ts": entry + 60,
                "net_pnl": pnl,
            }
        )
        entry += 60

    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)


def main() -> None:
    args = _parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    trades_csv = args.out_dir / "demo_trades.csv"
    _make_demo_trades_csv(trades_csv, n_trades=args.n_trades)

    result = generate_report_from_trades(
        trades_csv=trades_csv,
        out_dir=args.out_dir,
        prefix="demo",
        summary_json=None,
    )

    print(f"Wrote demo report to: {result.out_dir}")
    print(f"Trades CSV: {trades_csv}")
    print(f"Equity PNG: {result.paths.equity_png}")
    print(f"Drawdown PNG: {result.paths.drawdown_png}")
    print(f"Manifest: {result.manifest_json}")


if __name__ == "__main__":
    main()