#!/usr/bin/env bash
set -euo pipefail

EDGE_URL="${EDGE_URL:-https://edge.dhkalign.com}"
PHRASE="${1:-Rickshaw pabo na}"

echo "→ GET ${EDGE_URL}/translate?q=${PHRASE}"
curl -sS "${EDGE_URL}/translate" --get --data-urlencode "q=${PHRASE}"
echo -e "\n"

echo "→ POST ${EDGE_URL}/translate {\"text\":\"${PHRASE}\"}"
curl -sS -H "content-type: application/json" -d "{\"text\":\"${PHRASE}\"}" "${EDGE_URL}/translate"
echo
