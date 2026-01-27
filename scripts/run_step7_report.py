from __future__ import annotations

import argparse
from pathlib import Path

from src.reports.generate import generate_report_from_trades


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Step 7: generate report artifacts from trades.csv")
    p.add_argument(
        "--trades",
        type=Path,
        default=Path("data/outputs/trades.csv"),
        help="Path to trades.csv (must include net_pnl).",
    )
    p.add_argument(
        "--summary",
        type=Path,
        default=Path("data/outputs/summary.json"),
        help="Optional summary.json to embed into manifest.json.",
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=Path("reports/runs/step7"),
        help="Output folder for report artifacts.",
    )
    p.add_argument(
        "--prefix",
        type=str,
        default="",
        help="Optional filename prefix (useful for 1.0x / 2.0x cost runs).",
    )
    return p.parse_args()


def main() -> None:
    args = _parse_args()

    summary_path = args.summary if args.summary.exists() else None

    result = generate_report_from_trades(
        trades_csv=args.trades,
        out_dir=args.out_dir,
        prefix=args.prefix,
        summary_json=summary_path,
    )

    print(f"Wrote report to: {result.out_dir}")
    print(f"Equity CSV: {result.paths.equity_csv}")
    print(f"Equity PNG: {result.paths.equity_png}")
    print(f"Drawdown PNG: {result.paths.drawdown_png}")
    print(f"Manifest: {result.manifest_json}")


if __name__ == "__main__":
    main()