# DHK Align — Public README

DHK Align is an open-core, security-first Banglish ⇄ English translation engine designed to provide high-quality translations with flexible tiers.

---

## Overview

DHK Align offers two tiers:

- **Free Tier:** React SPA frontend with safe data, no API key required, limited to free translation packs.
- **Pro Tier:** API-key gated endpoints supporting premium packs and usage tracking, with optional GPT-4o-mini fallback for enhanced translation quality.

The system is built with a Cloudflare Worker as the public ingress and a Fly.io-hosted FastAPI backend that handles translation requests, caching, and metrics. GPT-4o-mini fallback is enabled to provide translations when the database does not have a match.

---

## Quick Start (Development)

**Prerequisites:**  
- Python >= 3.11  
- Node.js >= 18  
- jq, sqlite3, cloudflared, wrangler  

**Start Backend Server:**  
```bash
cd ~/Dev/dhkalign
export EDGE_SHIELD_TOKEN="$(grep -m1 '^EDGE_SHIELD_TOKEN=' infra/edge/.dev.vars | cut -d= -f2)" \
  EDGE_SHIELD_ENFORCE=1 BACKEND_CACHE_TTL=180
./scripts/run_server.sh   # Backend runs on http://127.0.0.1:8090
```

**Start Cloudflare Worker:**  
```bash
cd ~/Dev/dhkalign/infra/edge
BROWSER=false wrangler dev --local --ip 127.0.0.1 --port 8789 --config wrangler.toml
# Worker runs on http://127.0.0.1:8789
```

---

## Architecture

- **Frontend:** React SPA for free-tier users, communicating exclusively with the Cloudflare Worker.
- **Cloudflare Worker:** Handles all public requests, enforces CORS, rate limits, API key validation, and caching.
- **Backend (Fly.io):** FastAPI service managing translation logic, database access, GPT fallback, metrics, and audit logging.
- **Caching:** Two-layer caching with edge cache and backend TTL cache to optimize response times.
- **Translation Flow:** DB-first lookup → GPT-4o-mini fallback (if enabled) → auto-insert into DB → serve response.

---

## Security

- **Edge Shield:** Cloudflare Worker authenticates to backend using a secret token (`x-edge-shield` header).
- **API Authentication:** Pro endpoints require a valid `x-api-key`; admin endpoints require `x-admin-key`.
- **Rate Limiting:** Daily quotas per API key at the edge; IP-level limits on backend.
- **Audit Logs:** Append-only, HMAC-signed logs ensure traceability without storing user text.
- **Stripe Webhook:** Securely validated with signature and replay protection.
- **CORS:** Strictly enforced on all incoming requests.
- **Billing Key Endpoint:** Secure, single-use key retrieval restricted to allowlisted origins.

---

## Environment Variables

- `EDGE_SHIELD_TOKEN` — Secret token for backend authentication.
- `EDGE_SHIELD_ENFORCE` — Enable edge shield token enforcement.
- `BACKEND_CACHE_TTL` — Backend cache TTL in seconds.
- `CORS_ORIGINS` — Allowed origins for CORS.

### Backend (Fly.io) Variables

- `OPENAI_API_KEY` — OpenAI API key (required if GPT fallback enabled).
- `ENABLE_GPT_FALLBACK` — Set to `1` to enable GPT-4o-mini fallback.
- `GPT_MODEL` — Model name (default: `gpt-4o-mini`).
- `GPT_MAX_TOKENS` — Max tokens for GPT responses (default: `128`).
- `GPT_TIMEOUT_MS` — Timeout for GPT calls in milliseconds (default: `2000`).

---

## Contact

For inquiries or security issues, please reach out to:

- Info: [info@dhkalign.com](mailto:info@dhkalign.com)  
- Security: [admin@dhkalign.com](mailto:admin@dhkalign.com)

---

*© 2025 DHK Align. Code licensed under MIT. Data is proprietary.*