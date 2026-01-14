CREATE TABLE IF NOT EXISTS features (
  feature_id   SERIAL PRIMARY KEY,
  name         TEXT NOT NULL UNIQUE,          -- e.g. 'ret_1', 'rsi_14'
  description  TEXT,
  params       JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bar_feature_values (
  instrument_id INT NOT NULL REFERENCES instruments(instrument_id) ON DELETE CASCADE,
  timeframe     TEXT NOT NULL,
  ts            TIMESTAMPTZ NOT NULL,
  feature_id    INT NOT NULL REFERENCES features(feature_id) ON DELETE CASCADE,
  value         NUMERIC,
  PRIMARY KEY (instrument_id, timeframe, ts, feature_id)
);

-- Helpful indexes for queries
CREATE INDEX IF NOT EXISTS idx_bfv_feature_ts
  ON bar_feature_values (feature_id, ts);

CREATE INDEX IF NOT EXISTS idx_bfv_instr_tf_ts
  ON bar_feature_values (instrument_id, timeframe, ts);