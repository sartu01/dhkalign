# DHK Align — Execution Deliverables (October 2025)

This document summarizes the key operational details, deliverables, environment variables, and troubleshooting information for DHK Align as of October 2025.

---

## 🚀 MVP Deliverables & Milestones

- **Core stack:**  
  - Backend: FastAPI on Fly.io (`backend/data/translations.db`)  
  - Edge: Cloudflare Worker ingress (with KV namespaces `CACHE` and `USAGE`)  
  - Frontend: React SPA (free tier UI, safe data cache)  
  - GPT fallback: `gpt-4o-mini` model enabled for Pro tier fallback on DB misses  
  - Metrics: Prometheus-compatible endpoint exposing `dhk_db_hit_total`, `dhk_gpt_fallback_total`, `dhk_gpt_fail_total`, request latency  
  - Audit: HMAC-signed append-only JSONL logs (no user text stored)  
  - Security: Edge shield token, API key gating, admin key protection, CORS enforcement, rate limiting (edge + origin), replay prevention on Stripe webhook

- **API endpoints:**  
  - `/translate` (free) — POST (preferred) and GET supported  
  - `/translate/pro` (Pro) — requires `x-api-key`, supports `{"pack":"..."}`  
  - Admin routes: `/admin/health`, `/admin/cache_stats`, `/admin/keys/*`, `/admin/whoami` (admin key required)  
  - Stripe webhook: `/webhook/stripe` (secure signature validation, replay lock)  
  - Billing key: `/billing/key` (one-time key return, origin allowlisted)

- **Caching:**  
  - Two-layer caching: Edge Worker cache keyed by method+path+body, backend TTL cache with `X-Backend-Cache` header  
  - `?cache=no` query bypasses edge cache to backend

- **Security posture:**  
  - Origin requests require `x-edge-shield` token  
  - API keys for Pro endpoints  
  - Admin key for sensitive routes  
  - Rate limiting: daily per-API-key quotas at edge, IP-level limits at origin (SlowAPI)  
  - Stripe webhook strict validation and replay protection

---

## 🌐 Environment Variables

### Edge Worker

- `EDGE_SHIELD_TOKEN` — secret token for origin authentication (`x-edge-shield` header)  
- `EDGE_SHIELD_ENFORCE` — enable enforcement (set to `1`)  
- `BACKEND_CACHE_TTL` — backend cache TTL in seconds  
- `CORS_ORIGINS` — allowed origins for CORS  
- Admin key managed via Wrangler secrets or `.dev.vars`

### Backend (Fly.io)

- `OPENAI_API_KEY` — OpenAI API key (required if GPT fallback enabled)  
- `ENABLE_GPT_FALLBACK` — set to `1` to enable GPT fallback on DB miss  
- `GPT_MODEL` — GPT model name (default: `gpt-4o-mini`)  
- `GPT_MAX_TOKENS` — max tokens for fallback (default: `128`)  
- `GPT_TIMEOUT_MS` — GPT request timeout in ms (default: `2000`)

---

## 🧪 Curl Examples

### Edge Health Check
```bash
curl -s http://127.0.0.1:8789/edge/health | jq .
```

### Admin Cache Stats
```bash
curl -s -H "x-admin-key: your-admin-key" http://127.0.0.1:8789/admin/cache_stats | jq .
```

### Admin Key Management
```bash
# Add key (GET with ?key=...)
curl -H "x-admin-key: your-admin-key" "http://127.0.0.1:8789/admin/keys/add?key=newkey123"

# Check key
curl -H "x-admin-key: your-admin-key" "http://127.0.0.1:8789/admin/keys/check?key=newkey123"

# Delete key
curl -H "x-admin-key: your-admin-key" "http://127.0.0.1:8789/admin/keys/del?key=newkey123"
```

### Free Translation

```bash
# POST (canonical)
curl -sX POST http://127.0.0.1:8789/translate \
  -H 'Content-Type: application/json' \
  -d '{"text":"Bazar korbo"}' | jq

# GET (supported)
curl -s 'http://127.0.0.1:8789/translate?q=Bazar%20korbo' | jq
```

### Cache MISS → HIT

```bash
curl -is -X POST http://127.0.0.1:8789/translate \
  -H 'Content-Type: application/json' \
  -d '{"text":"Bazar korbo"}' | grep CF-Cache-Edge

curl -is -X POST http://127.0.0.1:8789/translate \
  -H 'Content-Type: application/json' \
  -d '{"text":"Bazar korbo"}' | grep CF-Cache-Edge
```

### Bypass Edge Cache (Backend TTL Cache)

```bash
curl -is -X POST "http://127.0.0.1:8789/translate?cache=no" \
  -H 'Content-Type: application/json' \
  -d '{"text":"Bazar korbo"}' | grep X-Backend-Cache
```

### Metrics Endpoint

```bash
curl -is https://backend.dhkalign.com/metrics | sed -n '1,8p'
curl -s  https://backend.dhkalign.com/metrics | egrep 'dhk_db_hit_total|dhk_gpt_fallback_total|dhk_gpt_fail_total' | sort
```

---

## 🛠 Troubleshooting Cheatsheet

| Symptom                          | Cause                                      | Fix                                               |
|---------------------------------|--------------------------------------------|--------------------------------------------------|
| Origin returns 403 (Worker→origin) | Missing/invalid `x-edge-shield` header    | Set correct `EDGE_SHIELD_TOKEN` and enable enforcement |
| Admin API calls fail with 401    | Missing/invalid `x-admin-key`               | Provide correct admin key in request header       |
| Rate limit exceeded error        | Too many requests per API key or IP         | Wait for quota reset or reduce request rate       |
| Cache always MISS                | Request differs in method/path/body         | Ensure identical requests; avoid `?cache=no` unless intended |
| Stripe webhook fails             | Missing/invalid `stripe-signature` header  | Verify webhook secret and timestamp tolerance     |
| Billing key endpoint unauthorized| Request from non-allowlisted origin          | Ensure request originates from allowlisted IP or Worker |

---

## 📂 Notes

- The backend enforces uniqueness on `(src_lang, roman_bn_norm, tgt_lang, pack)`; `id` is cosmetic.  
- Audit logs exclude user text for privacy.  
- All production secrets are managed via Wrangler secrets and Fly.io environment variables.  
- The Worker is the sole ingress point in production, enforcing all security and rate limits.

---

For further details, refer to the internal secured documentation (`private/docs/README_secured_MVP.md`).