#!/bin/bash
set -euo pipefail

APP="${APP:-dhkalign-backend}"
MODEL="${MODEL:-gpt-4o-mini}"
TOKENS="${TOKENS:-128}"
TIMEOUT_MS="${TIMEOUT_MS:-2000}"
OPENAI_API_KEY="${OPENAI_API_KEY:-}"

if [ -z "$OPENAI_API_KEY" ]; then
  echo "ERROR: Must set OPENAI_API_KEY=sk-..."
  exit 1
fi

flyctl secrets set -a "$APP" \
  OPENAI_API_KEY="$OPENAI_API_KEY" \
  ENABLE_GPT_FALLBACK="1" \
  GPT_MODEL="$MODEL" \
  GPT_MAX_TOKENS="$TOKENS" \
  GPT_TIMEOUT_MS="$TIMEOUT_MS"

flyctl deploy -a "$APP"
