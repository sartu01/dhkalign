#!/usr/bin/env bash
set -euo pipefail

PORT="${1:-8788}"
ADMIN_KEY="$(cat .secrets/ADMIN_KEY)"

echo "=== Edge health ==="
curl -s http://127.0.0.1:$PORT/edge/health | jq .

echo
echo "=== Admin cache stats ==="
curl -s -H "x-admin-key: $ADMIN_KEY" \
  http://127.0.0.1:$PORT/admin/cache_stats | jq .

echo
echo "=== Edge KV cache MISS/HIT test ==="
curl -is -X POST http://127.0.0.1:$PORT/translate \
  -H 'Content-Type: application/json' \
  -d '{"text":"kemon acho","src_lang":"banglish","dst_lang":"english"}' | grep -i CF-Cache-Edge || true
curl -is -X POST http://127.0.0.1:$PORT/translate \
  -H 'Content-Type: application/json' \
  -d '{"text":"kemon acho","src_lang":"banglish","dst_lang":"english"}' | grep -i CF-Cache-Edge || true

echo
echo "=== Backend TTL cache MISS/HIT test (bypass edge) ==="
curl -is -X POST "http://127.0.0.1:$PORT/translate?cache=no" \
  -H 'Content-Type: application/json' \
  -d '{"text":"kemon acho","src_lang":"banglish","dst_lang":"english"}' | grep -i X-Backend-Cache || true
curl -is -X POST "http://127.0.0.1:$PORT/translate?cache=no" \
  -H 'Content-Type: application/json' \
  -d '{"text":"kemon acho","src_lang":"banglish","dst_lang":"english"}' | grep -i X-Backend-Cache || true

echo
echo "=== Admin cache stats (after tests) ==="
curl -s -H "x-admin-key: $ADMIN_KEY" \
  http://127.0.0.1:$PORT/admin/cache_stats | jq .
