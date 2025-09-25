#!/usr/bin/env bash
set -euo pipefail

# Config
WORKER_URL="${WORKER_URL:-https://dhkalign-edge-production.tnfy4np8pm.workers.dev}"
SECRETS_FILE="${SECRETS_FILE:-$HOME/.dhkalign_secrets}"

# 0) Preflight
command -v wrangler >/dev/null || { echo "ERROR: wrangler not found"; exit 1; }
command -v openssl  >/dev/null || { echo "ERROR: openssl not found"; exit 1; }
command -v curl     >/dev/null || { echo "ERROR: curl not found"; exit 1; }

# 1) Fresh ADMIN_KEY → wrangler prod secret
ADMIN="$(openssl rand -hex 16)"
echo "New ADMIN_KEY generated."
printf "%s" "$ADMIN" | wrangler secret put ADMIN_KEY --env production >/dev/null
echo "ADMIN_KEY set in Worker (prod). Deploying Worker…"
wrangler deploy --env production >/dev/null
echo "Worker deployed."

# 2) Mint a prod API key (KV)
KEY="prod_$(openssl rand -hex 6)"
echo "Minting API key in KV: $KEY"
MINT_RESP="$(curl -s -w '\n%{http_code}' -H "x-admin-key: $ADMIN" "$WORKER_URL/admin/keys/add?key=$KEY")" || true
BODY="$(printf "%s" "$MINT_RESP" | sed '$d')"
CODE="$(printf "%s" "$MINT_RESP" | tail -n1)"
if [ "$CODE" != "200" ] && [ "$CODE" != "201" ]; then
  echo "ERROR: mint failed (HTTP $CODE). Body:" >&2
  echo "$BODY" >&2
  exit 2
fi

# 3) Save both secrets locally (secure file)
umask 177
touch "$SECRETS_FILE"
chmod 600 "$SECRETS_FILE"
{
  echo "# ---- $(date -u +'%Y-%m-%dT%H:%M:%SZ') ----"
  echo "ADMIN_KEY=$ADMIN"
  echo "PROD_API_KEY=$KEY"
} >> "$SECRETS_FILE"

# 4) Minimal confirm (masked)
echo
echo "Saved to $SECRETS_FILE"
echo "ADMIN_KEY: ${ADMIN:0:4}****${ADMIN: -4}"
echo "PROD_API_KEY: $KEY"
echo
echo "Tip: export for a shell session:"
echo "  source $SECRETS_FILE"
echo
echo "Next: call /translate/pro using your new PROD_API_KEY:"
echo "  curl -s -X POST \"$WORKER_URL/translate/pro\" \\"
echo "    -H 'content-type: application/json' -H \"x-api-key: $KEY\" \\"
echo "    -d '{\"text\":\"pocket khali, ki korbo\",\"src_lang\":\"bn-rom\",\"tgt_lang\":\"en\"}' | jq"
