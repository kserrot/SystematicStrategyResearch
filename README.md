# Systematic Strategy Research (Crypto)

Reproducible research project that pulls crypto market data, stores it in Postgres,
builds a feature dataset, and evaluates trading signals/backtests.

> Note: ML/modeling is intentionally deferred until the data + feature pipeline is solid.

## Tech Stack
- Python 3.11
- Postgres (Docker)
- SQLAlchemy
- Ruff + Pytest
- GitHub Actions CI

## Quickstart (Local Dev)
From the repo root:
```bash
docker compose up -d db adminer
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
python -m src.main
```

## Step 1: Data Layer MVP (1.1–1.4)
Goal: stand up a repeatable local data layer (Postgres in Docker) with a minimal OHLCV schema.

### 1.1 Start services
```bash
docker compose up -d db adminer
```

### 1.2 Apply schema SQL
All SQL migrations live in `sql/` and can be applied like this:

```bash
# apply the base schema migration
docker compose exec -T db psql -U ssrl -d ssrl < sql/001_schema.sql

# verify tables
docker compose exec db psql -U ssrl -d ssrl -c "\dt"
```

Expected core tables:
- `instruments`
- `ohlcv_bars`
- `ingest_runs`

### 1.3 Connectivity smoke test
```bash
docker compose exec db psql -U ssrl -d ssrl -c "SELECT 1 AS db_ok;"
```

### 1.4 Optional: Adminer UI
Open Adminer in your browser to inspect tables and run ad-hoc queries.


## Step 2: Data Ingestion + Resampling (2.1–2.4)
Goal: ingest a small, reproducible OHLCV sample into Postgres and create at least one higher timeframe via resampling.

### 2.1 Ingest sample OHLCV
```bash
# example ingestion script
python scripts/ingest_sample_ohlcv.py
```

### 2.2 Verify ingested bars
```bash
docker compose exec db psql -U ssrl -d ssrl -c "
SELECT i.exchange, i.symbol, b.timeframe, COUNT(*) bars,
       MIN(b.ts) AS first_ts, MAX(b.ts) AS last_ts
FROM ohlcv_bars b
JOIN instruments i ON i.instrument_id=b.instrument_id
GROUP BY 1,2,3
ORDER BY bars DESC;
"
```

### 2.3 Resample to a higher timeframe (e.g., 4h)
Use either SQL or Python resampling, but keep it **causal** (only aggregates past bars into the current bucket).

```bash
# apply your resampling SQL
docker compose exec -T db psql -U ssrl -d ssrl < sql/003_resample_4h.sql
```

### 2.4 Sanity check counts by timeframe
```bash
docker compose exec db psql -U ssrl -d ssrl -c "
SELECT timeframe, COUNT(*) AS bars
FROM ohlcv_bars
GROUP BY timeframe
ORDER BY timeframe;
"
```

## Step 3: Feature Engineering Pipeline (3.1–3.8)
This step validates the ingested OHLCV bars, defines a normalized feature store schema, computes core technical features, and writes feature values back to Postgres.

### 3.1 Data sanity checks (Postgres)
```bash
docker compose exec db psql -U ssrl -d ssrl -c "\dt"

docker compose exec db psql -U ssrl -d ssrl -c "
SELECT timeframe, COUNT(*) AS bars
FROM ohlcv_bars
GROUP BY timeframe
ORDER BY timeframe;
"
```

### 3.2 Create feature store tables
Apply the SQL in `sql/002_features.sql`:

```bash
# run local SQL file inside the db container
docker compose exec -T db psql -U ssrl -d ssrl < sql/002_features.sql

# verify tables
docker compose exec db psql -U ssrl -d ssrl -c "\dt"
```

Schema highlights:
- `features`: feature definitions (`name`, `description`, `params`)
- `bar_feature_values`: long-form values keyed by `(instrument_id, timeframe, ts, feature_id)`

### 3.3 Core feature functions
Core feature implementations live in `src/features/core.py` and are **causal** (no lookahead).

### 3.4 Build + write features to Postgres
```bash
# example: compute features for BTCUSDT 1h bars and upsert to bar_feature_values
python scripts/build_features.py --exchange binance --symbol BTCUSDT --timeframe 1h

# verify counts
docker compose exec db psql -U ssrl -d ssrl -c "
SELECT COUNT(*) AS n_features FROM features;
SELECT COUNT(*) AS n_feature_values FROM bar_feature_values;
"
```

### 3.5 Unit tests
```bash
pytest -q -m "not integration"
```

### 3.6 End-to-end smoke test (requires DB)
```bash
pytest -q -m integration
```

### 3.7 Validate feature distributions
```bash
python scripts/validate_features.py
```

### 3.8 Developer workflow
```bash
# lint + formatting
ruff check .
ruff format .

# tests
pytest -q -m "not integration"
```

### 3.10 CI (unit tests)
GitHub Actions runs Ruff + unit tests on every push/PR via `.github/workflows/ci.yml`.
Integration tests are marked with `@pytest.mark.integration` and are not run in CI by default.
