from __future__ import annotations

import argparse
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
from src.config.loader import load_yaml
from src.strategies.v1.entry import EntryRuleParams
from src.strategies.v1.spec import StrategyParams


def _first(value):
    """Return first element if value is a list/tuple, otherwise return value."""
    if isinstance(value, (list, tuple)):
        if not value:
            return None
        return value[0]
    return value


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/v1.yaml")
    args = ap.parse_args()

    cfg = load_yaml(args.config)

    costs_cfg = cfg.get("costs", {})
    sens_cfg = cfg.get("sensitivity", {})

    multipliers = sens_cfg.get("multipliers", [1.0])
    if not sens_cfg.get("enabled", True):
        multipliers = [1.0]

    # Synthetic bars to validate the full pipeline (limit fill + TP exit)
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

    base_params = StrategyParams(
        limit_expiry_bars=int(_first(cfg.get("params", {}).get("limit_expiry_bars", 3))),
        atr_stop_mult=float(_first(cfg.get("params", {}).get("atr_stop_mult", 1.0))),
        take_profit_r=float(_first(cfg.get("params", {}).get("take_profit_r", 2.0))),
        time_stop_bars=_first(cfg.get("params", {}).get("time_stop_bars", None)),
        maker_fee_bps=float(costs_cfg.get("maker_fee_bps", 0.0)),
        taker_fee_bps=float(costs_cfg.get("taker_fee_bps", 0.0)),
        slippage_bps=float(costs_cfg.get("slippage_bps", 0.0)),
    )

    out_dir = Path("data/outputs")
    out_dir.mkdir(parents=True, exist_ok=True)

    index_rows: list[dict[str, object]] = []

    for i, m in enumerate(multipliers):
        m = float(m)
        strat_params = StrategyParams(
            limit_expiry_bars=base_params.limit_expiry_bars,
            atr_stop_mult=base_params.atr_stop_mult,
            take_profit_r=base_params.take_profit_r,
            time_stop_bars=base_params.time_stop_bars,
            maker_fee_bps=base_params.maker_fee_bps * m,
            taker_fee_bps=base_params.taker_fee_bps * m,
            slippage_bps=base_params.slippage_bps * m,
        )

        trades = run_backtest_v1(
            df,
            symbol="SMOKE",
            params=strat_params,
            entry_params=EntryRuleParams(min_vol_ratio=None),
        )

        pnl_rows = [apply_costs(t, strat_params) for t in trades]
        net_pnls = [r.net_pnl for r in pnl_rows]
        metrics = compute_metrics(net_pnls)

        out_df = pd.DataFrame([r.__dict__ for r in pnl_rows])

        trades_path = out_dir / f"trades_{m:.1f}x.csv"
        summary_path = out_dir / f"summary_{m:.1f}x.json"

        out_df.to_csv(trades_path, index=False)

        payload = {
            "config_path": str(args.config),
            "multiplier": m,
            "params": {
                "limit_expiry_bars": strat_params.limit_expiry_bars,
                "atr_stop_mult": strat_params.atr_stop_mult,
                "take_profit_r": strat_params.take_profit_r,
                "time_stop_bars": strat_params.time_stop_bars,
                "maker_fee_bps": strat_params.maker_fee_bps,
                "taker_fee_bps": strat_params.taker_fee_bps,
                "slippage_bps": strat_params.slippage_bps,
            },
            "metrics": metrics_to_dict(metrics),
        }
        summary_path.write_text(json.dumps(payload, indent=2))

        # Keep existing filenames for the first run so other scripts keep working.
        if i == 0:
            (out_dir / "trades.csv").write_text(trades_path.read_text())
            (out_dir / "summary.json").write_text(summary_path.read_text())

        index_rows.append(
            {
                "multiplier": m,
                "trades_csv": str(trades_path),
                "summary_json": str(summary_path),
            }
        )

        print(f"Wrote {trades_path}")
        print(f"Wrote {summary_path}")

    (out_dir / "cost_sensitivity.json").write_text(json.dumps(index_rows, indent=2))
    print(f"Wrote {out_dir / 'cost_sensitivity.json'}")


if __name__ == "__main__":
    main()
