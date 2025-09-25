#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$HOME/Dev/dhkalign"
cd "$ROOT/infra/edge"

test -f wrangler.toml || { echo "wrangler.toml missing"; exit 1; }
test -f src/index.js || { echo "src/index.js missing"; exit 1; }
test -f src/stripe.js || { echo "src/stripe.js missing"; exit 1; }

if [ ! -f .dev.vars ]; then
  cat <<EOF
ERR: .dev.vars missing. Create it with:
ADMIN_KEY=your_admin_key
EDGE_SHIELD_TOKEN=your_edge_shield
STRIPE_WEBHOOK_SECRET=whsec_xxx
EOF
  exit 1
fi

echo "▶ verify ORIGIN_BASE_URL for prod before deploying prod later"
grep -n 'ORIGIN_BASE_URL' wrangler.toml || true

PORT=8789
echo "▶ wrangler dev on 127.0.0.1:$PORT"
BROWSER=false wrangler dev --local --ip 127.0.0.1 --port "$PORT" --config wrangler.toml
