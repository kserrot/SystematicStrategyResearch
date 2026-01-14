from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import pandas as pd
import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values

# ensure repo root is on sys.path so `import src...` works when running as a script
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.features.core import build_features  # noqa: E402

FEATURE_DEFS: list[tuple[str, str, dict]] = [
    ("ret_1", "Log return: log(close).diff()", {"kind": "return", "window": 1}),
    ("vol_20", "Rolling std of ret_1, window=20", {"kind": "vol", "window": 20}),
    ("sma_20", "Simple moving average of close, window=20", {"kind": "sma", "window": 20}),
    ("ema_20", "Exponential moving average of close, span=20", {"kind": "ema", "span": 20}),
    ("rsi_14", "Wilder RSI of close, window=14", {"kind": "rsi", "window": 14}),
    ("atr_14", "Wilder ATR, window=14", {"kind": "atr", "window": 14}),
    ("vwap_20", "Rolling VWAP approximation, window=20", {"kind": "vwap", "window": 20}),
    ("vwap_dist_20", "(close - vwap_20)/close", {"kind": "vwap_dist", "window": 20}),
]


def connect():
    load_dotenv(dotenv_path=REPO_ROOT / ".env")
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "ssrl"),
        user=os.getenv("DB_USER", "ssrl"),
        password=os.getenv("DB_PASSWORD", "ssrl"),
    )


def get_instrument_id(cur, exchange: str, symbol: str) -> int:
    cur.execute(
        """
        SELECT instrument_id
        FROM instruments
        WHERE exchange=%s AND symbol=%s
        """,
        (exchange, symbol),
    )
    row = cur.fetchone()
    if not row:
        raise ValueError(f"Instrument not found: {exchange} {symbol}")
    return int(row[0])


def fetch_bars(
    cur, instrument_id: int, timeframe: str, start: str | None, end: str | None
) -> pd.DataFrame:
    where = ["instrument_id=%s", "timeframe=%s"]
    params = [instrument_id, timeframe]

    if start:
        where.append("ts >= %s")
        params.append(start)
    if end:
        where.append("ts <= %s")
        params.append(end)

    sql = f"""
      SELECT ts, open, high, low, close, volume
      FROM ohlcv_bars
      WHERE {" AND ".join(where)}
      ORDER BY ts;
    """

    cur.execute(sql, tuple(params))
    rows = cur.fetchall()

    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"])
    return df


def upsert_feature_defs(cur) -> dict[str, int]:
    """
    Ensures FEATURE_DEFS exist in `features` table.
    Returns mapping: name -> feature_id
    """
    mapping: dict[str, int] = {}
    for name, desc, params in FEATURE_DEFS:
        cur.execute(
            """
            INSERT INTO features (name, description, params)
            VALUES (%s, %s, %s)
            ON CONFLICT (name) DO UPDATE
              SET description=EXCLUDED.description,
                  params=EXCLUDED.params
            RETURNING feature_id;
            """,
            (name, desc, json.dumps(params)),
        )
        mapping[name] = int(cur.fetchone()[0])
    return mapping


def write_feature_values(
    conn, instrument_id: int, timeframe: str, df_feat: pd.DataFrame, name_to_id: dict[str, int]
) -> int:
    """
    Writes long-form values into bar_feature_values with upsert.
    Returns number of rows prepared for insert.
    """
    feature_cols = [c for c in df_feat.columns if c.startswith("feature__")]
    if not feature_cols:
        raise ValueError("No feature__ columns found. Did build_features() run?")

    rows = []
    for _, r in df_feat.iterrows():
        ts = r["ts"]
        for col in feature_cols:
            val = r[col]
            if pd.isna(val):
                continue
            feature_name = col.replace("feature__", "")
            fid = name_to_id.get(feature_name)
            if fid is None:
                continue
            rows.append((instrument_id, timeframe, ts, fid, float(val)))

    if not rows:
        return 0

    insert_sql = """
      INSERT INTO bar_feature_values (instrument_id, timeframe, ts, feature_id, value)
      VALUES %s
      ON CONFLICT (instrument_id, timeframe, ts, feature_id)
      DO UPDATE SET value = EXCLUDED.value;
    """

    with conn.cursor() as cur:
        execute_values(cur, insert_sql, rows, page_size=5000)

    return len(rows)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--exchange", default="binance")
    p.add_argument("--symbol", default="BTCUSDT")
    p.add_argument("--timeframe", default="1h")
    p.add_argument("--start", default=None, help="ISO timestamp, e.g. 2026-01-01T00:00:00Z")
    p.add_argument("--end", default=None, help="ISO timestamp, e.g. 2026-01-10T00:00:00Z")
    args = p.parse_args()

    conn = connect()
    conn.autocommit = False

    try:
        with conn.cursor() as cur:
            instrument_id = get_instrument_id(cur, args.exchange, args.symbol)

            df = fetch_bars(cur, instrument_id, args.timeframe, args.start, args.end)
            if df.empty:
                raise ValueError("No bars returned for that instrument/timeframe/date range.")

            name_to_id = upsert_feature_defs(cur)
            conn.commit()

        df_feat = build_features(df)

        inserted = write_feature_values(conn, instrument_id, args.timeframe, df_feat, name_to_id)
        conn.commit()

        print(f"OK: bars={len(df)} feature_values_upserted={inserted}")

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
