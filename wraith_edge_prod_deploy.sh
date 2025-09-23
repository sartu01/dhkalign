#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$HOME/Dev/dhkalign"
cd "$ROOT/infra/edge"

if ! grep -q 'ORIGIN_BASE_URL = "https://backend.dhkalign.com"' wrangler.toml; then
  echo "ERR: ORIGIN_BASE_URL not set to https://backend.dhkalign.com in wrangler.toml"
  exit 1
fi

echo "If not set yet, run these once:"
echo "  wrangler secret put ADMIN_KEY --env production"
echo "  wrangler secret put EDGE_SHIELD_TOKEN --env production"
echo "  wrangler secret put STRIPE_WEBHOOK_SECRET --env production"
read -p "Deploy prod Worker now? [y/N] " ans
[[ "${ans:-N}" =~ ^[Yy]$ ]] || exit 0

wrangler deploy --env production
echo "✔ prod Worker deployed"
