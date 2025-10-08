# DHK Align — Banglish ⇄ English Translation Engine

> **Open-core, security-first translation engine.**  
> Free tier uses safe data; Pro tier is API-key gated with premium packs and optional GPT fallback.  

---

## 🌟 Overview

DHK Align is a secure, open-core translation engine designed for Banglish to English translation and vice versa. It consists of three main components: the Frontend, the Edge Worker, and the Backend. The system is designed for high security, efficient caching, and scalable usage with both free and pro tiers.

---

## 🖥️ Frontend

- **Technology:** React Single Page Application (SPA)  
- **Purpose:** Provides the user interface for free tier users and caches safe data on the client side.  
- **Communication:** The frontend communicates exclusively with the Edge Worker and does not talk directly to the backend.  

---

## 🌐 Edge Worker (Cloudflare Worker)

- **Hosting:** Runs on Cloudflare Workers, serving as the primary ingress point for both production and development environments.  
- **Responsibilities:**  
  - Acts as the gateway for all client requests.  
  - Handles caching, rate limiting, authentication, and routing.  
  - Enforces CORS policies on incoming requests.  
- **KV Namespaces:**  
  - `CACHE` — TTL-based response cache, indicated by `CF-Cache-Edge: HIT|MISS` headers.  
  - `USAGE` — per-API-key counters for daily quotas.  
- **Routes and Features:**  
  - **Health Checks:**  
    - `/edge/health` — Edge Worker health status.  
    - `/admin/health` — Admin health endpoint.  
  - **Admin API:**  
    - `/admin/cache_stats` — Cache statistics.  
    - `/admin/keys/add` — Add admin keys.  
    - `/admin/keys/check` — Check admin keys.  
    - `/admin/keys/del` — Delete admin keys.  
    - `/admin/whoami` — Returns environment names and origin/KV info; requires `x-admin-key`.  
  - **Billing:**  
    - `/billing/key` — Returns billing key once per request; origin allowlisted for security.  
  - **Translation:**  
    - `/translate` (free tier) — POST with JSON `{"text":"..."}` is canonical; GET with `?q=` supported.  
    - `/translate/pro` — Pro tier endpoint requiring `x-api-key` header for authentication.  
  - **Stripe Webhook:**  
    - `/webhook/stripe` — Accepts Stripe webhook events (only `checkout.session.completed`), requires `stripe-signature` header with 5-minute tolerance, and uses KV for replay attack prevention.  
  - **Miscellaneous:**  
    - `/` — Returns minimal JSON response.  
    - `/favicon.ico` — Returns HTTP 204 (no content) to avoid noisy 403 errors.  
- **Security and Authentication:**  
  - Origin requests require `x-edge-shield` header matching `EDGE_SHIELD_TOKEN`.  
  - Admin routes require `x-admin-key`.  
  - Pro routes require `x-api-key`.  
  - Clients never send `x-edge-shield`; only the Worker uses it internally when calling the backend.  
- **Rate Limiting and Quotas:**  
  - Daily per-API-key quotas are enforced using KV storage.  
  - CORS is enforced on all requests.  
- **Caching:**  
  - Two-layer caching system:  
    - Edge cache keyed by HTTP method + path + request body.  
    - Query parameter `?cache=no` bypasses edge cache and hits backend directly.  
- **Audit Logs:**  
  - Append-only HMAC-signed logs stored in `private/audit/security.jsonl`.  

---

## 🗄️ Backend (FastAPI on Fly.io)

- **Hosting:** Private origin hosted on Fly.io, running on port 8090.  
- **Purpose:** Handles translation logic, including database lookups and optional GPT fallback for Pro tier.  
- **Routes:**  
  - `/health` — Backend health check.  
  - `/translate` — Free tier translation endpoint.  
  - `/translate/pro` — Pro tier translation endpoint requiring `x-edge-shield` header from Worker.  
  - `/metrics` — Prometheus metrics endpoint.  
- **Functionality:**  
  - Supports DB-first translation lookup.  
  - Optional GPT fallback if enabled (`ENABLE_GPT_FALLBACK=1`), which attempts GPT translation on DB miss, inserts result into DB, and serves it.  
- **Request Format:**  
  - Preferred: POST with JSON body `{"text":"..."}`.  
  - Optional: `{"q":"..."}` may be supported but `text` is recommended.  
  - Pro tier requests may include `{"pack":"..."}` to specify premium packs.  
- **Caching:**  
  - Backend adds `X-Backend-Cache: HIT|MISS` header when edge cache is bypassed (`?cache=no`).  
- **Database:**  
  - Canonical DB path: `backend/data/translations.db`.  
  - Unique constraint enforced on `(src_lang, roman_bn_norm, tgt_lang, pack)`.  
  - `id` field is cosmetic only.  
- **Metrics:**  
  - Exposes metrics such as `dhk_db_hit_total`, `dhk_gpt_fallback_total`, `dhk_gpt_fail_total`, and request latency for monitoring and alerting.  

---

## 📊 System Diagram

```
Frontend (React SPA)
        ↓
Cloudflare Worker (Edge Worker)
        ↓
   Fly.io Backend (FastAPI)
        ↓
   Translation DB + GPT Fallback
```

- The React SPA sends requests to the Cloudflare Worker, which enforces security, caching, and quotas.  
- The Worker forwards requests to the Fly.io backend when necessary, adding authentication headers.  
- The backend serves translations from the database or GPT fallback and returns results with metrics headers.  
- The Worker caches responses and manages admin and billing endpoints.

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
# curl -X POST -H "x-admin-key: your-admin-key" -d '{"key":"newkey123"}' http://127.0.0.1:8789/admin/keys/add
```

**Free Translation**  
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

**Bypass Edge Cache (Backend TTL Cache)**  
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

- **Edge Shield:** All traffic routes through the Cloudflare Worker. Origin backend is blocked unless request includes a valid `x-edge-shield` header matching `EDGE_SHIELD_TOKEN`.  
- **Pro API Authentication:** `/translate/pro` requires an `x-api-key` header for authentication.  
- **Authentication Truth Table:**

  | Surface (client calls)          | `x-edge-shield` | `x-api-key` | `x-admin-key` |
  |---------------------------------|-----------------:|------------:|--------------:|
  | Edge `/translate` (free)        | No               | No          | No            |
  | Edge `/translate/pro`           | No               | **Yes**     | No            |
  | Edge `/admin/keys/*`            | No               | No          | **Yes**       |

  - The origin backend is private and only accepts requests with the `x-edge-shield` header from the Worker. Clients never send this header directly.  
- **Rate Limiting:**  
  - Edge quotas enforce daily per-API-key limits using KV storage (e.g., 1000 requests/day).  
  - Backend rate limiting (SlowAPI) applies per-IP for certain routes when enabled (e.g., 60 requests/min).  
- **CORS:** Strictly enforced on all incoming requests.  
- **Two-Layer Caching:**  
  - Edge cache keyed by HTTP method, path, and request body.  
  - Query parameter `?cache=no` bypasses edge cache and hits backend cache directly.  
- **Audit Logs:** Append-only, HMAC-signed JSONL logs that do not store user text.  
- **Stripe Webhook:** Requires `stripe-signature` header with 5-minute tolerance; only accepts `checkout.session.completed` events; replay attacks prevented via KV replay lock.  
- **Billing Key Endpoint:** `/billing/key` returns a key once per request and is origin allowlisted for security.  

---

## 📂 Repo Structure

See [repo-structure.txt](repo-structure.txt) for a clean tree view.

---

## 📚 Documentation

For detailed documentation, see the [docs/](docs/) folder:

- [Architecture](docs/ARCHITECTURE.md)  
- [Security](docs/SECURITY.md)  
- [Security Runbook](docs/SECURITY_RUNBOOK.md)  
- [Privacy](docs/PRIVACY.md)  
- [Execution Deliverables](docs/EXECUTION_DELIVERABLES.md)  
- [Contributing](docs/CONTRIBUTING.md)  
- [Next TODO](docs/NEXT_TODO.md)  

For internal operations and sensitive details, see `private/docs/README_secured_MVP.md` (not part of public GitHub).

---

## 🔄 Free vs Pro Split

- **Free Tier:**  
  - Client-side React SPA with safe data.  
  - No API key required.  
  - Limited to free translation packs.  
- **Pro Tier:**  
  - API-key gated endpoints (`/translate/pro`).  
  - Supports premium packs via `{"pack":"..."}` in request body.  
  - Usage tracked and rate-limited.  

---

## 🌐 Environment Variables

- `EDGE_SHIELD_TOKEN` — Secret token to authenticate origin requests to backend.  
- `EDGE_SHIELD_ENFORCE` — Enable enforcement of edge shield token.  
- `BACKEND_CACHE_TTL` — TTL for backend cache in seconds.  
- `CORS_ORIGINS` — Allowed origins for CORS.  
- Worker secrets are managed via Wrangler secrets for production and via `infra/edge/.dev.vars` for development.

### Backend (Fly.io) Environment Variables

- `OPENAI_API_KEY` — OpenAI API key (sk-…), required only if GPT fallback is enabled.  
- `ENABLE_GPT_FALLBACK` — Set to `1` to enable GPT fallback on DB miss.  
- `GPT_MODEL` — Model name (default: `gpt-4o-mini`).  
- `GPT_MAX_TOKENS` — Max tokens for fallback responses (default: `128`).  
- `GPT_TIMEOUT_MS` — Timeout in milliseconds (default: `2000`).  

---

## 🛠 Troubleshooting Cheatsheet

| Symptom                          | Possible Cause                         | Fix                                             |
|---------------------------------|--------------------------------------|-------------------------------------------------|
| Origin returns 403 in logs (Worker→origin) | Missing or invalid `x-edge-shield`   | Set correct EDGE_SHIELD_TOKEN in the Worker env; ensure enforcement is enabled |
| Admin API calls fail with 401    | Missing or invalid `x-admin-key`     | Provide correct admin key in header              |
| Rate limit exceeded error        | Too many requests per API key or IP  | Wait for quota reset or reduce request rate      |
| Cache not hitting (always MISS) | Request differs in method/path/body  | Ensure identical requests; avoid `?cache=no` unless intended |
| Stripe webhook fails             | Missing or invalid `stripe-signature`| Verify webhook secret and timestamp tolerance    |
| Billing key endpoint unauthorized| Request from non-allowlisted origin  | Ensure request comes from allowlisted IP or Worker|

---

## 🗂 Production Cutover Checklist

1. Set  
   `ORIGIN_BASE_URL` in `infra/edge/wrangler.toml` (both default and `[env.production]`) to `https://backend.dhkalign.com`.  
2. Configure Wrangler secrets with production keys (`EDGE_SHIELD_TOKEN`, `ADMIN_KEY`, API keys).  
3. Set backend secrets on Fly.io (optional fallback): `OPENAI_API_KEY`, `ENABLE_GPT_FALLBACK`, `GPT_MODEL`, `GPT_MAX_TOKENS`, `GPT_TIMEOUT_MS`; then deploy Fly app.  
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