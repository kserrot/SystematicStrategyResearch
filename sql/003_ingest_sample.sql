\set ON_ERROR_STOP on

INSERT INTO instruments(symbol, exchange, asset_class, base_currency, quote_currency)
VALUES ('BTCUSDT', 'binance', 'crypto', 'BTC', 'USDT')
ON CONFLICT (symbol, exchange) DO NOTHING;

SELECT instrument_id
FROM instruments
WHERE symbol='BTCUSDT' AND exchange='binance'
\gset

DROP TABLE IF EXISTS staging_ohlcv;
CREATE TEMP TABLE staging_ohlcv (
  ts     TIMESTAMPTZ,
  open   NUMERIC(18,8),
  high   NUMERIC(18,8),
  low    NUMERIC(18,8),
  close  NUMERIC(18,8),
  volume NUMERIC(28,10)
);

\copy staging_ohlcv(ts,open,high,low,close,volume) FROM '/tmp/btcusdt_1h_sample.csv' WITH (FORMAT csv, HEADER true);

INSERT INTO ohlcv_bars(instrument_id, timeframe, ts, open, high, low, close, volume, source)
SELECT :'instrument_id', '1h', ts, open, high, low, close, volume, 'generated'
FROM staging_ohlcv
ON CONFLICT (instrument_id, timeframe, ts) DO NOTHING;

INSERT INTO ingest_runs(source, status, rows_loaded, notes)
SELECT 'generated', 'success', COUNT(*), 'BTCUSDT 1h sample'
FROM staging_ohlcv;