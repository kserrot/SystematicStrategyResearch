from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import yaml

# Ensure repo root is on sys.path so "import src" works when running directly.
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.backtest.grid import run_walkforward_abc
from src.backtest.splits import make_abc_split_by_ts, pick_cutoffs_by_ratio


def _make_synthetic_df() -> pd.DataFrame:
    # Same synthetic dataset as the working smoke run.
    rows: list[dict[str, float]] = []
    ts = 0
    for _ in range(30):
        rows.append(
            {
                "ts": ts,
                "low": 9.8,
                "high": 10.2,
                "close": 9.9,
                "vwap": 10.0,
                "atr": 2.0,
                "ema50_1h": 101,
                "ema200_1h": 100,
            }
        )
        ts += 60
        rows.append(
            {
                "ts": ts,
                "low": 9.9,
                "high": 10.3,
                "close": 10.2,
                "vwap": 10.0,
                "atr": 2.0,
                "ema50_1h": 101,
                "ema200_1h": 100,
            }
        )
        ts += 60
        rows.append(
            {
                "ts": ts,
                "low": 9.95,
                "high": 10.05,
                "close": 10.01,
                "vwap": 10.0,
                "atr": 2.0,
                "ema50_1h": 101,
                "ema200_1h": 100,
            }
        )
        ts += 60
        rows.append(
            {
                "ts": ts,
                "low": 10.0,
                "high": 12.1,
                "close": 12.0,
                "vwap": 10.0,
                "atr": 2.0,
                "ema50_1h": 101,
                "ema200_1h": 100,
            }
        )
        ts += 60
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    args = ap.parse_args()

    cfg = yaml.safe_load(open(args.config))
    symbol = cfg["symbols"][0]

    # Step 6 plumbing: use synthetic data (like the smoke script).
    df = _make_synthetic_df()

    a_end_ts, b_end_ts = pick_cutoffs_by_ratio(df, a_ratio=0.6, b_ratio=0.8)
    split = make_abc_split_by_ts(df, a_end_ts=a_end_ts, b_end_ts=b_end_ts)

    # Minimal grid (same as smoke). Selection is currently by total_net_pnl in grid.py.
    costs = cfg.get("costs", {})
    maker_fee_bps = float(costs.get("maker_fee_bps", 2.0))
    slippage_bps = float(costs.get("slippage_bps", 1.0))

    grid = [
        {
            "strategy": {
                "limit_expiry_bars": 3,
                "atr_stop_mult": 1.0,
                "take_profit_r": 1.0,
                "time_stop_bars": None,
                "maker_fee_bps": maker_fee_bps,
                "slippage_bps": slippage_bps,
            },
            "entry": {"min_vol_ratio": None},
        },
        {
            "strategy": {
                "limit_expiry_bars": 3,
                "atr_stop_mult": 1.0,
                "take_profit_r": 2.0,
                "time_stop_bars": None,
                "maker_fee_bps": maker_fee_bps,
                "slippage_bps": slippage_bps,
            },
            "entry": {"min_vol_ratio": None},
        },
    ]

    out = run_walkforward_abc(
        train=split.train,
        validate=split.validate,
        test=split.test,
        symbol=symbol,
        grid=grid,
    )

    out_dir = Path("data/outputs")
    out_dir.mkdir(parents=True, exist_ok=True)

    out["train_grid_runs"].to_csv(out_dir / "step6_runs.csv", index=False)

    payload = {
        "best_params": out["best_params"],
        "validate_metrics": out["validate_metrics"],
        "test_metrics": out["test_metrics"],
        "cutoffs": {"a_end_ts": a_end_ts, "b_end_ts": b_end_ts},
    }
    (out_dir / "step6_best.json").write_text(json.dumps(payload, indent=2))

    print(f"Wrote {out_dir / 'step6_runs.csv'}")
    print(f"Wrote {out_dir / 'step6_best.json'}")


if __name__ == "__main__":
    main()
