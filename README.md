# Systematic Strategy Research (Crypto)

Reproducible research project that pulls crypto market data, stores it in Postgres,
builds features, trains models, and evaluates trading signals/backtests.

## Tech Stack
- Python 3.11
- Postgres (Docker)
- SQLAlchemy
- Ruff + Pytest
- GitHub Actions CI

## Quickstart (Local Dev)
```bash
docker compose up -d db adminer
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
python -m src.main
