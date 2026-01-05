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