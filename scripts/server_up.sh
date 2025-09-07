#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# Load secrets and flags
export EDGE_SHIELD_TOKEN="$(cat .secrets/EDGE_SHIELD_TOKEN)"
export EDGE_SHIELD_ENFORCE=1
export BACKEND_CACHE_TTL="${BACKEND_CACHE_TTL:-180}"

# Start FastAPI backend (Uvicorn)
./scripts/run_server.sh
