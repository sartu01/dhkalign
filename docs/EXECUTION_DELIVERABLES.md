# DHK Align — Public README

This is the public-facing README for DHK Align.

The full **Secured MVP README** with internal architecture and sensitive details has been moved to `private/docs/README_secured_MVP.md` and is **not intended for public GitHub**.

For general documentation, see [docs/](docs/).

# DHK Align — Banglish ⇄ English Translation Engine

> **Open-core, security-first translation engine.**  
> Free tier uses safe data; Pro tier is API-key gated with premium packs and optional GPT fallback.  

---

## 🌟 Overview

- **Frontend:** React SPA (free tier UI, client cache for safe data). The frontend only calls the Edge Worker.
- **Edge Worker:** Cloudflare Worker is the only ingress in prod/dev.  
  - KV namespaces:  
    - `CACHE` — TTL response cache (`CF-Cache-Edge: HIT|MISS`)  
    - `USAGE` — per-API-key counters (daily quotas)  
  - Admin routes: `/edge/health`, `/admin/health`, `/admin/cache_stats`, `/admin/keys/add`, `/admin/keys/check`, `/admin/keys/del`
  - Stripe webhook: `/webhook/stripe` (requires `stripe-signature` header, 5-min tolerance, only `checkout.session.completed` events accepted, replay lock with KV)
  - Billing key handoff: `/billing/key` (returns key once, origin allowlisted)
  - Free translate: "/translate" (POST {"text":"..."} canonical; GET ?q= supported)
  - Root & favicon: "/" returns minimal JSON; "/favicon.ico" returns 204 (no more noisy 403s)
  - Admin whoami: "/admin/whoami" (names-only env + origin/kv info; requires x-admin-key)
  - CORS enforcement applied.
- **Backend:** FastAPI (private origin, port 8090) behind the Worker.  
  - Routes: `/health`, `/translate`, `/translate/pro`  
  - Pro fallback (optional): DB-first → GPT fallback (if enabled) → auto-insert into DB → serve
  - Metrics: "/metrics" (Prometheus) — db_hit, gpt_fallback, gpt_fail, request latency
  - Backend API requires POST requests with JSON body `{"text":"..."}` (preferred); `{"q":"..."}` may be supported but `text` is recommended. Optional `{"pack":"..."}` for Pro tier.  
  - TTL cache: adds `X-Backend-Cache: HIT|MISS` when bypassing edge cache (`?cache=no`)  
  - Audit: HMAC-signed append-only logs (`private/audit/security.jsonl`)  
  - Canonical DB path: `backend/data/translations.db`  
  - DB identity guarantee: uniqueness enforced on `(src_lang, roman_bn_norm, tgt_lang, pack)`; `id` is cosmetic only.

---

## ⚡ Quick Start (Dev, 2 Tabs)

**Prerequisites**  
- Python >= 3.11  
- Node.js >= 18  
- jq  
- sqlite3  
- cloudflared  
- wrangler

**Server tab**  
Canonical:  
```bash
cd ~/Dev/dhkalign
# load dev shield token from Worker dev vars
export EDGE_SHIELD_TOKEN="$(grep -m1 '^EDGE_SHIELD_TOKEN=' infra/edge/.dev.vars | cut -d= -f2)" \
  EDGE_SHIELD_ENFORCE=1 BACKEND_CACHE_TTL=180
./scripts/run_server.sh   # backend on http://127.0.0.1:8090
```
Legacy/alternative:  
```bash
./scripts/server_up.sh
```

**Work tab**  
```bash
cd ~/Dev/dhkalign/infra/edge
BROWSER=false wrangler dev --local --ip 127.0.0.1 --port 8789 --config wrangler.toml
# Worker on http://127.0.0.1:8789
```

**Secrets**  
- Development secrets are loaded from `infra/edge/.dev.vars`.  
- Production secrets are managed via Wrangler secrets.

---

## 🧪 Curl Tests

**Edge health**  
```bash
curl -s http://127.0.0.1:8789/edge/health | jq .
```

**Admin cache stats**  
```bash
curl -s -H "x-admin-key: your-admin-key" \
  http://127.0.0.1:8789/admin/cache_stats | jq .
```

**Admin key management**  
```bash
# Add key (GET with ?key=...)
curl -H "x-admin-key: your-admin-key" \
  "http://127.0.0.1:8789/admin/keys/add?key=newkey123"

# Check key (GET with ?key=...)
curl -H "x-admin-key: your-admin-key" \
  "http://127.0.0.1:8789/admin/keys/check?key=newkey123"

# Delete key (GET with ?key=...)
curl -H "x-admin-key: your-admin-key" \
  "http://127.0.0.1:8789/admin/keys/del?key=newkey123"

# (Optional) POST JSON is also supported if enabled in the Worker:
# curl -X POST -H "x-admin-key: your-admin-key" \
#   -d '{"key":"newkey123"}' http://127.0.0.1:8789/admin/keys/add
```

**Free**
```bash
# POST (canonical)
curl -sX POST http://127.0.0.1:8789/translate \
  -H 'Content-Type: application/json' \
  -d '{"text":"Bazar korbo"}' | jq

# GET (also supported)
curl -s 'http://127.0.0.1:8789/translate?q=Bazar%20korbo' | jq
```

**Cache MISS → HIT**  
```bash
curl -is -X POST http://127.0.0.1:8789/translate \
  -H 'Content-Type: application/json' \
  -d '{"text":"Bazar korbo"}' | grep CF-Cache-Edge

curl -is -X POST http://127.0.0.1:8789/translate \
  -H 'Content-Type: application/json' \
  -d '{"text":"Bazar korbo"}' | grep CF-Cache-Edge
```

**Bypass edge (backend TTL cache)**  
```bash
curl -is -X POST "http://127.0.0.1:8789/translate?cache=no" \
  -H 'Content-Type: application/json' \
  -d '{"text":"Bazar korbo"}' | grep X-Backend-Cache
```

**Metrics**
```bash
curl -is https://backend.dhkalign.com/metrics | sed -n '1,8p'
curl -s  https://backend.dhkalign.com/metrics | egrep 'dhk_db_hit_total|dhk_gpt_fallback_total|dhk_gpt_fail_total' | sort
```

---

## 🔐 Security Posture

- **Edge shield:** all traffic goes through Cloudflare Worker; origin blocked unless header matches `EDGE_SHIELD_TOKEN` (`x-edge-shield` header).  
- **Pro API:** `/translate/pro` requires `x-api-key` header for authentication.  

**Authentication truth table**

| Surface (client calls)          | `x-edge-shield` | `x-api-key` | `x-admin-key` |
|---------------------------------|-----------------:|------------:|--------------:|
| Edge `/translate` (free)        | No               | No          | No            |
| Edge `/translate/pro`           | No               | **Yes**     | No            |
| Edge `/admin/keys/*`            | No               | No          | **Yes**       |

**Origin is private.** When the Worker calls origin `/translate/pro`, it sends `x-edge-shield: <token>` internally. Clients never send `x-edge-shield`.

- **Rate limiting:**  
  - **Edge Worker enforces daily per-API-key quotas (KV-backed; e.g., 1000/day).**  
  - **Origin applies IP-level rate limiting (SlowAPI 60/min) only when enabled on routes.**  
- **CORS:** enforced on all incoming requests.  
- **Two-layer caching:**  
  - Edge cache keyed by HTTP method + path + request body.  
  - Query parameter `?cache=no` bypasses edge cache and hits backend directly, which returns `X-Backend-Cache: HIT|MISS`.  
- **Audit logs:** append-only HMAC JSONL, no user text stored.  
- **Stripe webhook:** requires `stripe-signature` header with 5-minute tolerance, only accepts `checkout.session.completed` events, replay attacks prevented via KV replay lock.  
- **Billing key endpoint:** `/billing/key` returns key once per request, origin allowlisted for security.

---

## 📂 Repo Structure

See [repo-structure.txt](repo-structure.txt) for a clean tree view.

---

## 📚 Documentation

For detailed docs, see the [docs/](docs/) folder:

- [Architecture](docs/ARCHITECTURE.md)  
- [Security](docs/SECURITY.md)  
- [Security Runbook](docs/SECURITY_RUNBOOK.md)  
- [Privacy](docs/PRIVACY.md)  
- [Execution Deliverables](docs/EXECUTION_DELIVERABLES.md)  
- [Contributing](docs/CONTRIBUTING.md)  
- [Next TODO](docs/NEXT_TODO.md)  

For internal ops and sensitive details, see `private/docs/README_secured_MVP.md` (not part of public GitHub).

---

## 🔄 Free vs Pro Split

- **Free tier:** client-side React SPA with safe data, no API key required, limited to free packs.  
- **Pro tier:** API-key gated endpoints (`/translate/pro`), supports premium packs via `{"pack":"..."}` in request body, usage tracked and rate-limited.

---

## 🌐 Environment Variables

- `EDGE_SHIELD_TOKEN` — secret token to authenticate origin requests to backend.  
- `EDGE_SHIELD_ENFORCE` — enable enforcement of edge shield token.  
- `BACKEND_CACHE_TTL` — TTL for backend cache in seconds.  
- `CORS_ORIGINS` — allowed origins for CORS.  
- Worker secrets managed via Wrangler secrets for production, `infra/edge/.dev.vars` for development.

### Backend (Fly) Environment Variables
- `OPENAI_API_KEY` — OpenAI key (sk-…), required only if fallback is enabled
- `ENABLE_GPT_FALLBACK` — set to `1` to enable GPT fallback on DB miss
- `GPT_MODEL` — model name (default: `gpt-4o-mini`)
- `GPT_MAX_TOKENS` — max tokens for fallback responses (default: `128`)
- `GPT_TIMEOUT_MS` — timeout in milliseconds (default: `2000`)

---

## 🛠 Troubleshooting Cheatsheet

| Symptom                          | Possible Cause                         | Fix                                             |
|---------------------------------|--------------------------------------|-------------------------------------------------|
| Origin returns 403 in logs (Worker→origin) | Missing/invalid `x-edge-shield` on Worker call | Set correct EDGE_SHIELD_TOKEN in Worker env; ensure enforcement is enabled |
| Admin API calls fail with 401    | Missing or invalid `x-admin-key`     | Provide correct admin key in header              |
| Rate limit exceeded error        | Too many requests per API key or IP  | Wait for quota reset or reduce request rate      |
| Cache not hitting (always MISS) | Request differs in method/path/body  | Ensure identical requests; avoid `?cache=no` unless intended |
| Stripe webhook fails             | Missing or invalid `stripe-signature`| Verify webhook secret and timestamp tolerance    |
| Billing key endpoint unauthorized| Request from non-allowlisted origin  | Ensure request comes from allowlisted IP or Worker|

---

## 🗂 Production Cutover Checklist

1. Set `ORIGIN_BASE_URL` in `infra/edge/wrangler.toml` (both default and `[env.production]`) to https://backend.dhkalign.com.
2. Configure Wrangler secrets with production keys (`EDGE_SHIELD_TOKEN`, `ADMIN_KEY`, API keys).  
3. Set backend secrets on Fly (optional fallback): OPENAI_API_KEY, ENABLE_GPT_FALLBACK, GPT_MODEL, GPT_MAX_TOKENS, GPT_TIMEOUT_MS; then deploy Fly app.
4. Deploy Worker with `wrangler deploy --env production`.
5. Configure Stripe webhook endpoint and secret in Stripe dashboard.  
6. Verify admin and API keys work as expected.  
7. Confirm rate limiting and caching behavior in production.  
8. Schedule backups and audit log monitoring.

---

## 📄 License & Contact

- **Code:** MIT License. See `LICENSE_CODE.md` file.  
- **Data:** Proprietary license. See `LICENSE_DATA.md` file.

Contact:  
- Info: [info@dhkalign.com](mailto:info@dhkalign.com)  
- Security: [admin@dhkalign.com](mailto:admin@dhkalign.com)