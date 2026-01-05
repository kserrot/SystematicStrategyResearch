#!/usr/bin/env bash
set -e

docker compose up -d db adminer
echo "DB/Adminer up."
echo "Activate venv and run:"
echo "  source .venv/bin/activate"
echo "  python -m src.main"