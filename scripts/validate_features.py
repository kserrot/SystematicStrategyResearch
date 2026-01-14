from __future__ import annotations

import os
import warnings
from pathlib import Path

import pandas as pd
import psycopg2
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(dotenv_path=REPO_ROOT / ".env")

# pandas warns when using a raw DBAPI connection (psycopg2). We intentionally use it here
# to keep dependencies minimal; silence only this specific warning.
warnings.filterwarnings(
    "ignore",
    message=r"pandas only supports SQLAlchemy connectable.*",
    category=UserWarning,
)


def connect():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "ssrl"),
        user=os.getenv("DB_USER", "ssrl"),
        password=os.getenv("DB_PASSWORD", "ssrl"),
    )


def main():
    exchange = os.getenv("VAL_EXCHANGE", "binance")
    symbol = os.getenv("VAL_SYMBOL", "BTCUSDT")
    timeframe = os.getenv("VAL_TIMEFRAME", "1h")
    limit_bars = int(os.getenv("VAL_LIMIT", "120"))

    conn = connect()

    # 1) find instrument_id
    inst = pd.read_sql(
        """
        SELECT instrument_id
        FROM instruments
        WHERE exchange=%s AND symbol=%s
        """,
        conn,
        params=(exchange, symbol),
    )
    if inst.empty:
        raise SystemExit(f"Instrument not found: {exchange} {symbol}")
    instrument_id = int(inst.iloc[0]["instrument_id"])

    # 2) pull last N bars (ts only) to define the window
    bars = pd.read_sql(
        """
        SELECT ts
        FROM ohlcv_bars
        WHERE instrument_id=%s AND timeframe=%s
        ORDER BY ts DESC
        LIMIT %s
        """,
        conn,
        params=(instrument_id, timeframe, limit_bars),
    )
    if bars.empty:
        raise SystemExit("No bars found for that instrument/timeframe.")
    bars = bars.sort_values("ts").reset_index(drop=True)

    start_ts = bars["ts"].min()
    end_ts = bars["ts"].max()

    # 3) pull feature values for that same window
    feat_long = pd.read_sql(
        """
        SELECT v.ts, f.name AS feature, v.value
        FROM bar_feature_values v
        JOIN features f ON f.feature_id = v.feature_id
        WHERE v.instrument_id=%s
          AND v.timeframe=%s
          AND v.ts >= %s
          AND v.ts <= %s
        ORDER BY v.ts, f.name
        """,
        conn,
        params=(instrument_id, timeframe, start_ts, end_ts),
    )

    conn.close()

    # 4) pivot to wide form (easy to inspect)
    wide = feat_long.pivot_table(
        index="ts", columns="feature", values="value", aggfunc="first"
    ).reset_index()

    print("\n=== Window ===")
    print(f"{exchange} {symbol} {timeframe} | rows={len(bars)} | {start_ts} -> {end_ts}")

    print("\n=== Feature columns ===")
    print(sorted([c for c in wide.columns if c != "ts"]))

    print("\n=== Tail (last 5 rows) ===")
    print(wide.tail(5).to_string(index=False))

    # 5) quick sanity stats for key features (if present)
    def stats(col: str):
        if col not in wide.columns:
            return
        s = pd.to_numeric(wide[col], errors="coerce")
        print(f"\n--- {col} ---")
        print(s.describe().to_string())
        print("na_count =", int(s.isna().sum()))

    for c in ["ret_1", "vol_20", "sma_20", "ema_20", "rsi_14", "atr_14", "vwap_20", "vwap_dist_20"]:
        stats(c)

    # 6) a couple simple “range checks” (not failing, just printing)
    if "rsi_14" in wide.columns:
        rsi = pd.to_numeric(wide["rsi_14"], errors="coerce").dropna()
        print("\nRSI range:", float(rsi.min()), "to", float(rsi.max()))

    if "vwap_dist_20" in wide.columns:
        vd = pd.to_numeric(wide["vwap_dist_20"], errors="coerce").dropna()
        print("VWAP dist range:", float(vd.min()), "to", float(vd.max()))

    print("\nOK: validation complete")


if __name__ == "__main__":
    main()
