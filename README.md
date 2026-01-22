# Systematic Strategy Research (Crypto)

Reproducible research project that pulls crypto market data, stores it in Postgres,
builds a feature dataset, and evaluates trading signals/backtests.


## Tech Stack
- Python 3.12
- Postgres (Docker)
- SQLAlchemy
- Ruff + Pytest
- Matplotlib (reporting)
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


## Step 4: Strategy + Backtest (4.1–4.10)
Goal: implement a realistic v1 strategy backtest loop (limit orders + brackets), add costs/metrics, walk-forward evaluation, and basic reporting artifacts.

### 4.1 Limit-order fill model
- Place limit order on the **next bar** after the signal
- Fill rule: `low <= limit_px <= high`
- Expire after N bars

### 4.2 Strategy rules (v1)
- Trend filter (1h): `EMA50 > EMA200`
- Entry (10m): close crosses above VWAP (optional volume confirmation)

### 4.3 Backtest engine (state machine)
- `FLAT -> ORDER_PENDING -> IN_POSITION`
- Deterministic iteration with no lookahead

### 4.4 Exits (brackets)
- ATR-based stop
- R-multiple take profit
- Conservative same-bar ordering: stop first if both touched

### 4.5 Costs + metrics + exports
- Maker fee + slippage (bps)
- Writes `data/outputs/trades.csv` and `data/outputs/summary.json`

### 4.6 Walk-forward (A/B/C splits + grid)
- Select best parameters on train (A) by **total_net_pnl**
- Evaluate on validate (B) and test (C)
- Writes `data/outputs/wf_runs.csv` and `data/outputs/wf_best.json`

### 4.7 Reporting
- Equity curve + drawdown plots
- Writes `data/outputs/equity.csv`, `equity_curve.png`, `drawdown.png`

### 4.8 No-lookahead tests
- Next-bar order placement test
- ATR sourced from fill bar (not future)

### Quickstart (Step 4 smoke runs)
```bash
# deterministic smoke backtest + exports
python scripts/run_backtest_smoke.py

# reporting artifacts (equity + drawdown)
python scripts/make_report.py

# walk-forward smoke run (A/B/C + grid)
python scripts/run_walkforward_smoke.py
```

## Step 5: Costs + Realism Layer (Config-Driven) (5.1–5.4)
Goal: apply fees + slippage realistically, make costs reproducible via config, and run a quick sensitivity test (e.g., 2× costs).

### 5.1 Cost model
- Slippage (bps) applied adverse on entry + exit
- Fees (bps) applied on notional:
  - Entry: maker fee
  - Exit: taker fee for STOP / TAKE_PROFIT / TIME_STOP (otherwise maker)

### 5.2 Config file
Costs and sensitivity settings live in `configs/v1.yaml`:
- `costs.maker_fee_bps`, `costs.taker_fee_bps`, `costs.slippage_bps`
- `sensitivity.enabled`, `sensitivity.multipliers`

### 5.3 Run cost sensitivity (1× vs 2×)
```bash
# runs with config + writes both default outputs and multiplier-suffixed outputs
python scripts/run_backtest_smoke.py --config configs/v1.yaml

# reporting artifacts (equity + drawdown) from data/outputs/trades.csv
python scripts/make_report.py
```

Expected outputs:
- `data/outputs/trades.csv`, `data/outputs/summary.json` (first multiplier; keeps other scripts working)
- `data/outputs/trades_1.0x.csv`, `data/outputs/summary_1.0x.json`
- `data/outputs/trades_2.0x.csv`, `data/outputs/summary_2.0x.json`
- `data/outputs/cost_sensitivity.json`


### 5.4 Repo hygiene
Generated files under `data/outputs/` are ignored via `.gitignore` (folder kept with `data/outputs/.gitkeep`).

## Step 6: Walk-Forward Evaluation (A/B/C) on Real Data (6.1–6.4)
Goal: run a proper A/B/C walk-forward loop on **real DB data**: optimize on Train (A), select on Validate (B), and report out-of-sample results on Test (C).

### 6.1 Configure A/B/C split
Walk-forward settings live in `configs/v1.yaml`:
- `walkforward.single_split.train_start`, `train_end`
- `walkforward.single_split.val_end`
- `walkforward.single_split.test_end`
- `walkforward.selection_metric` (v1: `total_net_pnl`)

Example window (UTC):
- Train (A): 2025-12-25 → 2026-01-01
- Validate (B): 2026-01-02 → 2026-01-05
- Test (C): 2026-01-06 → 2026-01-08

### 6.2 Run Step 6 on real Postgres data
This script loads BTCUSDT bars + features from Postgres, computes EMA50/EMA200 from close (so the trend filter can run), performs the A/B/C split, runs a parameter sweep, selects the best params on B, then evaluates on C.

```bash
# ensure DB is running
docker compose up -d db

# run Step 6 on real DB data
PYTHONPATH="$(pwd)" python scripts/run_step6_real_db.py --config configs/v1.yaml
```

Outputs:
- `data/outputs/step6_real_runs.csv` (train-grid results)
- `data/outputs/step6_real_best.json` (selected params + validate/test metrics)

### 6.3 Sanity-check bar counts per split
```bash
docker compose exec db psql -U ssrl -d ssrl -c "
with bars as (
  select b.ts
  from ohlcv_bars b
  join instruments i on i.instrument_id=b.instrument_id
  where i.symbol='BTCUSDT' and b.timeframe='1h'
)
select
  sum(case when ts <= '2026-01-01 23:59:59+00' then 1 else 0 end) as train_bars,
  sum(case when ts >  '2026-01-01 23:59:59+00' and ts <= '2026-01-05 23:59:59+00' then 1 else 0 end) as val_bars,
  sum(case when ts >  '2026-01-05 23:59:59+00' then 1 else 0 end) as test_bars
from bars;"
```

### 6.4 Tests
A minimal walk-forward split test ensures A/B/C windows do not overlap:
```bash
pytest -q
```
