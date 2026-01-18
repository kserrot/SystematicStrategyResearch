from __future__ import annotations

import sys
from pathlib import Path

# ruff: noqa: E402
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.reports.equity_report import build_equity_curve, save_report


def main() -> None:
    trades_csv = Path("data/outputs/trades.csv")
    out_dir = Path("data/outputs")

    if not trades_csv.exists():
        raise FileNotFoundError(
            "Missing data/outputs/trades.csv. Run: python scripts/run_backtest_smoke.py"
        )

    eq = build_equity_curve(trades_csv)
    paths = save_report(eq, out_dir)

    print(f"Wrote {paths.equity_csv}")
    print(f"Wrote {paths.equity_png}")
    print(f"Wrote {paths.drawdown_png}")


if __name__ == "__main__":
    main()