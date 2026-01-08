# Load sample bars
from __future__ import annotations

import os
import csv
from pathlib import Path
import psycopg2

CSV_PATH = Path("data/raw/btcusdt_1h_sample.csv")
TIMEFRAME = "1h"
SYMBOL = "BTCUSDT"
EXCHANGE = "binance"
SOURCE = "generated"

def main() -> None:
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = int(os.getenv("DB_PORT", "5432"))
    db_name = os.getenv("DB_NAME", "postgres")
    db_user = os.getenv("DB_USER", "postgres")
    db_pass = os.getenv("DB_PASSWORD", "postgres")

    conn = psycopg2.connect(
        host=db_host, port=db_port, dbname=db_name, user=db_user, password=db_pass
    )
    conn.autocommit = False

    with conn.cursor() as cur:
        # Upsert instrument
        cur.execute(
            """
            INSERT INTO instruments(symbol, exchange, asset_class, base_currency, quote_currency)
            VALUES (%s, %s, 'crypto', 'BTC', 'USDT')
            ON CONFLICT (symbol, exchange) DO UPDATE SET symbol = EXCLUDED.symbol
            RETURNING instrument_id;
            """,
            (SYMBOL, EXCHANGE),
        )
        instrument_id = cur.fetchone()[0]

        # Insert bars
        loaded = 0
        with CSV_PATH.open() as f:
            r = csv.DictReader(f)
            for row in r:
                cur.execute(
                    """
                    INSERT INTO ohlcv_bars(instrument_id, timeframe, ts, open, high, low, close, volume, source)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (instrument_id, timeframe, ts) DO NOTHING;
                    """,
                    (
                        instrument_id,
                        TIMEFRAME,
                        row["ts"],
                        row["open"],
                        row["high"],
                        row["low"],
                        row["close"],
                        row["volume"],
                        SOURCE,
                    ),
                )
                loaded += 1

        # Log run
        cur.execute(
            """
            INSERT INTO ingest_runs(source, status, rows_loaded, notes)
            VALUES (%s, 'success', %s, %s);
            """,
            (SOURCE, loaded, f"{SYMBOL} {TIMEFRAME} sample"),
        )

    conn.commit()
    conn.close()
    print(f"Inserted ~{loaded} bars into Postgres.")

if __name__ == "__main__":
    main()