#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$HOME/Dev/dhkalign"
cd "$ROOT"

BASE="http://127.0.0.1:8789"
AK=$(grep -m1 '^ADMIN_KEY=' infra/edge/.dev.vars | cut -d= -f2)

echo "▶ edge health"
curl -sf "$BASE/edge/health" | jq .

KEY="dev_$(openssl rand -hex 4)"
echo "▶ add key: $KEY"
curl -s -H "x-admin-key: $AK" "$BASE/admin/keys/add?key=$KEY" | jq .

echo "▶ free translate via edge (MISS then HIT)"
curl -i -s "$BASE/translate?q=hello" | sed -n '1,20p' | egrep -i 'HTTP|CF-Cache-Edge'
curl -i -s "$BASE/translate?q=hello" | sed -n '1,20p' | egrep -i 'HTTP|CF-Cache-Edge'

echo "▶ pro translate via edge"
curl -s -X POST "$BASE/translate/pro" \
  -H "content-type: application/json" \
  -H "x-api-key: $KEY" \
  -d '{"text":"arre yar"}' | jq .

echo "▶ del key"
curl -s -H "x-admin-key: $AK" "$BASE/admin/keys/del?key=$KEY" | jq .
