from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

# Ensure repo root is on sys.path so "import src" works when running this file directly.
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.backtest.costs import apply_costs
from src.backtest.engine import run_backtest_v1
from src.backtest.metrics import compute_metrics, metrics_to_dict
from src.strategies.v1.entry import EntryRuleParams
from src.strategies.v1.spec import StrategyParams


def main() -> None:
    df = pd.DataFrame(
        [
            {
                "ts": 0,
                "low": 9.8,
                "high": 10.2,
                "close": 9.9,
                "vwap": 10.0,
                "atr": 2.0,
                "ema50_1h": 101,
                "ema200_1h": 100,
            },
            {
                "ts": 60,
                "low": 9.9,
                "high": 10.3,
                "close": 10.2,
                "vwap": 10.0,
                "atr": 2.0,
                "ema50_1h": 101,
                "ema200_1h": 100,
            },
            {
                "ts": 120,
                "low": 9.95,
                "high": 10.05,
                "close": 10.01,
                "vwap": 10.0,
                "atr": 2.0,
                "ema50_1h": 101,
                "ema200_1h": 100,
            },
            {
                "ts": 180,
                "low": 10.0,
                "high": 14.1,
                "close": 14.0,
                "vwap": 10.0,
                "atr": 2.0,
                "ema50_1h": 101,
                "ema200_1h": 100,
            },
        ]
    )

    params = StrategyParams(
        limit_expiry_bars=3,
        atr_stop_mult=1.0,
        take_profit_r=2.0,
        time_stop_bars=None,
        maker_fee_bps=2.0,
        slippage_bps=1.0,
    )

    trades = run_backtest_v1(
        df,
        symbol="SMOKE",
        params=params,
        entry_params=EntryRuleParams(min_vol_ratio=None),
    )

    pnl_rows = [apply_costs(t, params) for t in trades]
    net_pnls = [r.net_pnl for r in pnl_rows]

    metrics = compute_metrics(net_pnls)

    out_dir = Path("data/outputs")
    out_dir.mkdir(parents=True, exist_ok=True)

    out_df = pd.DataFrame([r.__dict__ for r in pnl_rows])
    out_df.to_csv(out_dir / "trades.csv", index=False)

    payload = {
        "params": {
            "limit_expiry_bars": params.limit_expiry_bars,
            "atr_stop_mult": params.atr_stop_mult,
            "take_profit_r": params.take_profit_r,
            "time_stop_bars": params.time_stop_bars,
            "maker_fee_bps": params.maker_fee_bps,
            "slippage_bps": params.slippage_bps,
        },
        "metrics": metrics_to_dict(metrics),
    }
    (out_dir / "summary.json").write_text(json.dumps(payload, indent=2))

    print(f"Wrote {out_dir / 'trades.csv'}")
    print(f"Wrote {out_dir / 'summary.json'}")


if __name__ == "__main__":
    main()