CREATE TABLE IF NOT EXISTS assets (
  asset_id TEXT PRIMARY KEY,
  symbol   TEXT NOT NULL,
  name     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS prices_daily (
  asset_id TEXT NOT NULL REFERENCES assets(asset_id),
  day      DATE NOT NULL,
  open     DOUBLE PRECISION,
  high     DOUBLE PRECISION,
  low      DOUBLE PRECISION,
  close    DOUBLE PRECISION,
  volume   DOUBLE PRECISION,
  PRIMARY KEY (asset_id, day)
);

CREATE INDEX IF NOT EXISTS idx_prices_daily_day ON prices_daily(day);

-- Core schema for SSR Platform

CREATE TABLE IF NOT EXISTS instruments (
  instrument_id  SERIAL PRIMARY KEY,
  symbol         TEXT NOT NULL,
  exchange       TEXT NOT NULL,
  asset_class    TEXT NOT NULL DEFAULT 'crypto',
  quote_currency TEXT,
  base_currency  TEXT,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(symbol, exchange)
);

CREATE TABLE IF NOT EXISTS ohlcv_bars (
  instrument_id  INT NOT NULL REFERENCES instruments(instrument_id) ON DELETE CASCADE,
  timeframe      TEXT NOT NULL,                 -- e.g. '1m', '5m', '1h', '1d'
  ts             TIMESTAMPTZ NOT NULL,          -- bar open time
  open           NUMERIC(18,8) NOT NULL,
  high           NUMERIC(18,8) NOT NULL,
  low            NUMERIC(18,8) NOT NULL,
  close          NUMERIC(18,8) NOT NULL,
  volume         NUMERIC(28,10) NOT NULL DEFAULT 0,
  source         TEXT NOT NULL DEFAULT 'local',
  PRIMARY KEY (instrument_id, timeframe, ts)
);

CREATE INDEX IF NOT EXISTS idx_ohlcv_time
  ON ohlcv_bars (timeframe, ts);

CREATE TABLE IF NOT EXISTS ingest_runs (
  run_id       SERIAL PRIMARY KEY,
  started_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  ended_at     TIMESTAMPTZ,
  source       TEXT NOT NULL,
  status       TEXT NOT NULL DEFAULT 'running',
  rows_loaded  INT NOT NULL DEFAULT 0,
  notes        TEXT
);