#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$HOME/Dev/dhkalign"
cd "$ROOT"
source backend/.venv/bin/activate

PORT=8090
echo "▶ start backend on :$PORT"
python -m uvicorn backend.main:app --host 127.0.0.1 --port "$PORT" --reload & BE_PID=$!

echo "▶ wait for /health"
for i in {1..30}; do
  curl -fsS "http://127.0.0.1:$PORT/health" >/dev/null && break
  sleep 1
done
curl -s "http://127.0.0.1:$PORT/health" | jq .

echo "▶ list paths"
curl -s "http://127.0.0.1:$PORT/openapi.json" | jq -r '.paths | keys[]' | sort

echo "▶ free translate via /api/translate"
curl -s "http://127.0.0.1:$PORT/api/translate?q=kemon%20acho" | jq .

echo "ℹ pro route is edge-gated; test via Worker"
echo "▶ backend running (PID $BE_PID). Ctrl+C here to stop, or: kill $BE_PID"
wait $BE_PID
