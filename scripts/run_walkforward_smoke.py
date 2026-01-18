from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

# Ensure repo root is on sys.path so "import src" works when running directly.
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.backtest.grid import run_walkforward_abc
from src.backtest.splits import make_abc_split_by_ts, pick_cutoffs_by_ratio


def main() -> None:
    # Synthetic data long enough to split and to differentiate parameter sets.
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
        # Exit bar: high only reaches 12.1 (so r=1 TP=12 hits, r=2 TP=14 doesn't)
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

    df = pd.DataFrame(rows)

    a_end_ts, b_end_ts = pick_cutoffs_by_ratio(df, a_ratio=0.6, b_ratio=0.8)
    split = make_abc_split_by_ts(df, a_end_ts=a_end_ts, b_end_ts=b_end_ts)

    grid = [
        {
            "strategy": {
                "limit_expiry_bars": 3,
                "atr_stop_mult": 1.0,
                "take_profit_r": 1.0,
                "time_stop_bars": None,
                "maker_fee_bps": 2.0,
                "slippage_bps": 1.0,
            },
            "entry": {"min_vol_ratio": None},
        },
        {
            "strategy": {
                "limit_expiry_bars": 3,
                "atr_stop_mult": 1.0,
                "take_profit_r": 2.0,
                "time_stop_bars": None,
                "maker_fee_bps": 2.0,
                "slippage_bps": 1.0,
            },
            "entry": {"min_vol_ratio": None},
        },
    ]

    out = run_walkforward_abc(
        train=split.train,
        validate=split.validate,
        test=split.test,
        symbol="WF_SMOKE",
        grid=grid,
    )

    out_dir = Path("data/outputs")
    out_dir.mkdir(parents=True, exist_ok=True)

    runs_df = out["train_grid_runs"]
    runs_df.to_csv(out_dir / "wf_runs.csv", index=False)

    payload = {
        "best_params": out["best_params"],
        "validate_metrics": out["validate_metrics"],
        "test_metrics": out["test_metrics"],
        "cutoffs": {"a_end_ts": a_end_ts, "b_end_ts": b_end_ts},
    }
    (out_dir / "wf_best.json").write_text(json.dumps(payload, indent=2))

    print(f"Wrote {out_dir / 'wf_runs.csv'}")
    print(f"Wrote {out_dir / 'wf_best.json'}")


if __name__ == "__main__":
    main()