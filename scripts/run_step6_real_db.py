from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path

import pandas as pd
import yaml
from sqlalchemy import text

# Allow `from src...` imports when running as a script.
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.backtest.grid import run_walkforward_abc
from src.backtest.splits import make_abc_split_by_ts
from src.db.engine import get_engine


def _utc_day_end_ts(date_str: str) -> int:
    # date_str like "2026-01-01" -> end of that UTC day (seconds)
    ts = pd.Timestamp(date_str, tz="UTC") + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    return int(ts.timestamp())


def _build_grid(cfg: dict) -> list[dict]:
    params = cfg.get("params", {})
    costs = cfg.get("costs", {})

    limit_expiry_bars = params.get("limit_expiry_bars", [3])
    atr_stop_mult = params.get("atr_stop_mult", [1.0])
    take_profit_r = params.get("take_profit_r", [2.0])
    time_stop_bars = params.get("time_stop_bars", [None])

    maker_fee_bps = float(costs.get("maker_fee_bps", 0.0))
    slippage_bps = float(costs.get("slippage_bps", 0.0))

    grid: list[dict] = []
    for leb, atrm, tpr, tsb in itertools.product(
        limit_expiry_bars, atr_stop_mult, take_profit_r, time_stop_bars
    ):
        grid.append(
            {
                "strategy": {
                    "limit_expiry_bars": int(leb),
                    "atr_stop_mult": float(atrm),
                    "take_profit_r": float(tpr),
                    "time_stop_bars": None if tsb in (None, "null") else int(tsb),
                    "maker_fee_bps": maker_fee_bps,
                    "slippage_bps": slippage_bps,
                },
                "entry": {"min_vol_ratio": None},
            }
        )
    return grid


def _load_symbol_frame(symbol: str, timeframe: str) -> pd.DataFrame:
    engine = get_engine()

    with engine.connect() as conn:
        instr_id = conn.execute(
            text("select instrument_id from instruments where symbol = :s"),
            {"s": symbol},
        ).scalar()

        if instr_id is None:
            raise ValueError(f"Symbol not found in instruments: {symbol}")

        # Bars
        bars = pd.read_sql(
            text(
                """
                select ts, open, high, low, close, volume
                from ohlcv_bars
                where instrument_id = :iid and timeframe = :tf
                order by ts
                """
            ),
            conn,
            params={"iid": int(instr_id), "tf": timeframe},
        )

        # Features (pivot bar_feature_values)
        feats = pd.read_sql(
            text(
                """
                select b.ts, f.name, b.value
                from bar_feature_values b
                join features f on f.feature_id = b.feature_id
                where b.instrument_id = :iid and b.timeframe = :tf
                order by b.ts
                """
            ),
            conn,
            params={"iid": int(instr_id), "tf": timeframe},
        )

    if bars.empty:
        raise ValueError(f"No bars found for {symbol} timeframe={timeframe}")

    if feats.empty:
        raise ValueError(
            f"No features found for {symbol} timeframe={timeframe}. "
            f"(Your DB currently only has 1h features.)"
        )

    feats_wide = feats.pivot_table(
        index="ts", columns="name", values="value", aggfunc="last"
    ).reset_index()

    df = bars.merge(feats_wide, on="ts", how="left")

    # Convert ts (timestamp) -> unix seconds int for the split/backtest code
    df["ts"] = pd.to_datetime(df["ts"], utc=True).astype("int64") // 1_000_000_000

    # Ensure numeric columns are floats (read_sql may return Decimals)
    for col in ["open", "high", "low", "close", "volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in df.columns:
        if col in {"ts"}:
            continue
        if df[col].dtype == object:
            df[col] = pd.to_numeric(df[col], errors="ignore")

    # Map feature names to what the strategy code typically expects
    if "vwap_20" in df.columns and "vwap" not in df.columns:
        df["vwap"] = pd.to_numeric(df["vwap_20"], errors="coerce")
    if "atr_14" in df.columns and "atr" not in df.columns:
        df["atr"] = pd.to_numeric(df["atr_14"], errors="coerce")

    # Compute EMA50 / EMA200 from close so the trend filter can work on real data
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df["ema50_1h"] = df["close"].ewm(span=50, adjust=False).mean()
    df["ema200_1h"] = df["close"].ewm(span=200, adjust=False).mean()

    # Order and drop rows missing core values
    df = df.sort_values("ts").reset_index(drop=True)
    df = df.dropna(subset=["open", "high", "low", "close"])

    return df


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    args = ap.parse_args()

    cfg = yaml.safe_load(open(args.config))
    symbol = cfg["symbols"][0]
    tf = cfg["timeframe"]["trade"]

    df = _load_symbol_frame(symbol=symbol, timeframe=tf)

    print(f"Loaded {len(df)} rows for {symbol} timeframe={tf}")
    if len(df) > 0:
        print(f"Range: ts[{df['ts'].min()}..{df['ts'].max()}]")

    # Basic signal diagnostics (helps explain 0-trade runs)
    if "vwap" in df.columns:
        cross_up = (df["close"] > df["vwap"]) & (df["close"].shift(1) <= df["vwap"].shift(1))
        print(f"VWAP cross-up count: {int(cross_up.sum())}")
    if "ema50_1h" in df.columns and "ema200_1h" in df.columns:
        trend_ok = df["ema50_1h"] > df["ema200_1h"]
        print(f"Trend OK (ema50>ema200) bars: {int(trend_ok.sum())} / {len(df)}")

    wf = cfg["walkforward"]["single_split"]
    a_end_ts = _utc_day_end_ts(wf["train_end"])
    b_end_ts = _utc_day_end_ts(wf["val_end"])

    split = make_abc_split_by_ts(df, a_end_ts=a_end_ts, b_end_ts=b_end_ts)

    grid = _build_grid(cfg)

    out = run_walkforward_abc(
        train=split.train,
        validate=split.validate,
        test=split.test,
        symbol=symbol,
        grid=grid,
    )

    out_dir = Path("data/outputs")
    out_dir.mkdir(parents=True, exist_ok=True)

    out["train_grid_runs"].to_csv(out_dir / "step6_real_runs.csv", index=False)

    payload = {
        "symbol": symbol,
        "timeframe": tf,
        "cutoffs": {"a_end_ts": a_end_ts, "b_end_ts": b_end_ts},
        "best_params": out["best_params"],
        "validate_metrics": out["validate_metrics"],
        "test_metrics": out["test_metrics"],
    }
    (out_dir / "step6_real_best.json").write_text(json.dumps(payload, indent=2) + "\n")

    print(f"Wrote {out_dir / 'step6_real_runs.csv'}")
    print(f"Wrote {out_dir / 'step6_real_best.json'}")


if __name__ == "__main__":
    main()
