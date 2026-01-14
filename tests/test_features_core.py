import os
import subprocess
import sys

import numpy as np
import pandas as pd
import psycopg2
import pytest
from dotenv import load_dotenv

from src.features.core import atr, build_features, log_return, rolling_vwap, rsi


def make_df(n=60):
    # simple synthetic OHLCV, increasing close
    ts = pd.date_range("2026-01-01", periods=n, freq="H", tz="UTC")
    close = pd.Series(np.linspace(100, 160, n))
    df = pd.DataFrame(
        {
            "ts": ts,
            "open": close - 0.5,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": np.full(n, 100.0),
        }
    )
    return df


def test_log_return_alignment():
    close = pd.Series([100.0, 110.0, 121.0])
    r = log_return(close)
    # log(110/100) and log(121/110)
    assert np.isclose(r.iloc[1], np.log(1.1))
    assert np.isclose(r.iloc[2], np.log(1.1))


def test_rsi_range():
    df = make_df(80)
    out = rsi(df["close"], 14)
    valid = out.dropna()
    assert (valid >= 0).all()
    assert (valid <= 100).all()


def test_atr_non_negative():
    df = make_df(80)
    out = atr(df["high"], df["low"], df["close"], 14)
    valid = out.dropna()
    assert (valid >= 0).all()


def test_rolling_vwap_defined_after_window():
    df = make_df(30)
    v = rolling_vwap(df, 20)
    # first 19 should be NaN, rest should be finite
    assert v.iloc[:19].isna().all()
    assert np.isfinite(v.iloc[19:]).all()


def test_build_features_columns_exist():
    df = make_df(60)
    out = build_features(df)

    expected = [
        "feature__ret_1",
        "feature__vol_20",
        "feature__sma_20",
        "feature__ema_20",
        "feature__rsi_14",
        "feature__atr_14",
        "feature__vwap_20",
        "feature__vwap_dist_20",
    ]
    for c in expected:
        assert c in out.columns


def test_no_lookahead_on_sma():
    df = make_df(60)
    out = build_features(df)

    # SMA_20 at index i should equal mean of close[i-19:i+1]
    i = 25
    sma_i = out.loc[i, "feature__sma_20"]
    manual = out.loc[i - 19 : i, "close"].mean()
    assert np.isclose(sma_i, manual)


@pytest.mark.integration
def test_e2e_build_features_script_writes_to_db():
    """End-to-end smoke test: run the feature builder script and confirm DB has rows."""
    # Load .env explicitly (prevents dotenv AssertionError in this execution style)
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    load_dotenv(dotenv_path=os.path.join(repo_root, ".env"))

    # If DB isn't reachable, skip instead of failing unit test suite
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            dbname=os.getenv("DB_NAME", "ssrl"),
            user=os.getenv("DB_USER", "ssrl"),
            password=os.getenv("DB_PASSWORD", "ssrl"),
        )
    except Exception as e:
        pytest.skip(f"DB not reachable for integration test: {e}")

    # Run the script on a small window; idempotent upsert is fine
    cmd = [
        sys.executable,
        os.path.join(repo_root, "scripts", "build_features.py"),
        "--exchange",
        "binance",
        "--symbol",
        "BTCUSDT",
        "--timeframe",
        "1h",
        "--start",
        "2026-01-01T00:00:00Z",
        "--end",
        "2026-01-03T00:00:00Z",
    ]

    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, f"Script failed. stdout={r.stdout}\nstderr={r.stderr}"

    # Verify at least some rows exist for ret_1 in the window
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT instrument_id FROM instruments WHERE exchange=%s AND symbol=%s",
                ("binance", "BTCUSDT"),
            )
            instrument_id = cur.fetchone()[0]

            cur.execute("SELECT feature_id FROM features WHERE name=%s", ("ret_1",))
            feature_id = cur.fetchone()[0]

            cur.execute(
                """
                SELECT COUNT(*)
                FROM bar_feature_values
                WHERE instrument_id=%s
                  AND timeframe=%s
                  AND feature_id=%s
                  AND ts >= %s
                  AND ts <= %s;
                """,
                (
                    instrument_id,
                    "1h",
                    feature_id,
                    "2026-01-01T00:00:00Z",
                    "2026-01-03T00:00:00Z",
                ),
            )
            n = cur.fetchone()[0]

    conn.close()
    assert n > 0
