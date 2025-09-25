#!/bin/bash
set -euo pipefail

APP_WORKER="https://dhkalign-edge-production.tnfy4np8pm.workers.dev"

# Use ADMIN from env or fall back to .dev.vars
ADMIN_KEY="${ADMIN:-$(grep -m1 '^ADMIN_KEY=' infra/edge/.dev.vars | cut -d= -f2)}"

if [ -z "$ADMIN_KEY" ]; then
  echo "ERROR: No ADMIN key set. Export ADMIN=... or put it in infra/edge/.dev.vars"
  exit 1
fi

KEY="prod_$(openssl rand -hex 6)"
resp=$(curl -s -H "x-admin-key: $ADMIN_KEY" "$APP_WORKER/admin/keys/add?key=$KEY")

if echo "$resp" | grep -q '"ok":true'; then
  echo "$resp"
  echo "KEY=$KEY"
else
  echo "mint failed (HTTP 401?) → check your ADMIN key"
  echo "$resp"
fi
