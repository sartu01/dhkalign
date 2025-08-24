#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source backend/.venv/bin/activate
export PYTHONPATH="$(pwd)"
python -m uvicorn backend.app_sqlite:app --host 127.0.0.1 --port 8090 --reload \
  --env-file backend/.env \
  --reload-exclude 'backend/.venv/*' \
  --reload-exclude 'frontend/node_modules/*' \
  --reload-exclude 'private/*'
