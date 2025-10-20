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
  - **Free (Edge)**: `GET /api/translate?q=...` (canonical), `POST /translate` (JSON `{ "q": "..." }`)
  - **Pro (Edge)**: `POST /translate/pro` — requires `x-api-key`
  - **Admin (Edge, allowlisted)**: `GET /admin/health`, `GET /admin/cache_stats`, `GET /admin/whoami`, `GET /admin/keys/(add|check|del)?key=...` (requires `x-admin-key`)
  - **Billing (Edge)**: `GET /billing/key?session_id=...` (one‑time key handoff; origin allowlisted)
  - **Webhook (Edge)**: `POST /webhook/stripe` (signature verify + replay lock)
  - **Origins (private)**:
    - **FastAPI**: `/health`, `/version`, `/translate`, `/translate/pro`, `/metrics`
    - **Go sidecar**: `/go/health`, `/go/version`, `/go/translate?q=...` (stub; parked)

- **Caching:**  
  - Two-layer caching: Edge Worker cache keyed by method+path+body, backend TTL cache with `X-Backend-Cache` header  
  - `?cache=no` query bypasses edge cache to backend

- **Security posture:**  
  - Origin requests require `x-edge-shield` token  
  - API keys for Pro endpoints  
  - Admin key for sensitive routes  
  - Rate limiting: daily per-API-key quotas at edge, IP-level limits at origin (SlowAPI)  
  - Stripe webhook strict validation and replay protection
  - Edge injects `x-edge-shield` to origins; clients never send it. Cache headers: `CF-Cache-Edge: HIT|MISS` at edge and `X-Backend-Cache: HIT|MISS` at origin (when edge is bypassed).

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
# POST (JSON) — dev Worker
curl -sX POST http://127.0.0.1:8789/translate \
  -H 'Content-Type: application/json' \
  -d '{"q":"Bazar korbo"}' | jq

# GET (canonical path) — dev Worker
curl -s 'http://127.0.0.1:8789/api/translate?q=Bazar%20korbo' | jq

# GET (legacy path still supported) — dev Worker
curl -s 'http://127.0.0.1:8789/translate?q=Bazar%20korbo' | jq
```
## One‑Minute Verification (prod)

```bash
# Front door
curl -sI https://dhkalign.com | head -n1
curl -sI https://www.dhkalign.com/test?q=1 | head -n1   # expect 301 to apex

# Edge + origin probes
curl -fsS https://edge.dhkalign.com/version | jq
curl -fsS https://backend.dhkalign.com/health | jq

# Free translate via Edge (GET and POST)
curl -fsS 'https://edge.dhkalign.com/api/translate?q=Rickshaw%20pabo%20na' | jq
curl -fsS -X POST 'https://edge.dhkalign.com/translate' -H 'content-type: application/json' \
  -d '{"q":"Rickshaw pabo na"}' | jq
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
# DHK Align — Execution Deliverables (Oct 2025)

Single, up‑to‑date summary of what is **shipped**, how it **operates**, and the **commands** you need to verify or troubleshoot. Harmonized with: `ARCHITECTURE.md`, `OPS.md`, `API.md`, `PROPERTY_DEFENSE.md`, `PRIVACY.md`.

---

## 1) MVP Deliverables & Milestones (shipped)

**Core stack**
- **Edge (Cloudflare Worker)** — single public ingress; strict CORS/headers; quotas; KV caches. Routes: **/edge/health**, **/version**, **/api/translate**, **/translate**, **/translate/pro**, **/billing/key**, **/admin/**\*, **/webhook/stripe**.
- **FastAPI origin (Fly.io, prod)** — `/health`, `/version`, `/translate`, `/translate/pro`, `/metrics`; DB‑first; optional GPT fallback inserts minimal pairs.
- **Go sidecar origin (Fly.io, parity)** — `/go/health`, `/go/version`, `/go/translate` (stub). **Deployed and parked (scale 0)**.
- **Frontend (Cloudflare Pages)** — SPA (CRA → Vite soon); build output `frontend/build` (→ `frontend/dist` after Vite).
- **Data** — SQLite at `backend/data/translations.db`; safety ≤ 1 (free), ≥ 2 (pro).

**Security posture**
- Worker adds **`x‑edge‑shield`** to origin calls (clients never send it).
- **Pro** route requires **`x‑api-key`**; **Admin** routes require **`x‑admin-key`**.
- Stripe webhook: signature verify + KV replay lock; billing handoff: `GET /billing/key?session_id=…` (origin allowlisted).

**Caching**
- **Edge KV** cache with `CF-Cache-Edge: HIT|MISS`; bypass with `?cache=no`.
- **Origin TTL** cache with `X-Backend-Cache: HIT|MISS` (visible when edge bypassed).

**Observability**
- Prometheus metrics (origin): `dhk_db_hit_total`, `dhk_gpt_fallback_total`, `dhk_gpt_fail_total`, request latency.
- HMAC‑signed local audit logs (no text) for security events; ≤ 90‑day retention.

**CI / Protections**
- **Required checks on `main`**: `["Cloudflare Pages","smoke"]` (speed mode).  
- **Smoke**: apex 200; `www` → apex 301; Edge `/version` tolerant; backend health tolerant + Fly fallback; **Go sidecar health** (non‑blocking; host auto‑derived from `backend-go/fly.toml`); free translate tolerant.

---

## 2) Public Surfaces (aligned with API.md)

**Edge (public)**
- `GET /edge/health` — edge health  
- `GET /version` — build SHA  
- `GET /api/translate?q=…` — **Free** translate (DB‑first)  
- `POST /translate` — **Free** translate (JSON)  
- `POST /translate/pro` — **Pro** translate (key‑gated)  
- `GET /billing/key?session_id=…` — one‑time key handoff after checkout  
- `GET /admin/keys/(add|check|del)?key=…` — admin key ops  
- `GET /admin/health`, `GET /admin/cache_stats`, `GET /admin/whoami` — admin diagnostics (key‑gated)

**Origins (private)**
- **FastAPI** — `GET /health`, `GET /version`, `POST /translate`, `POST /translate/pro`, `GET /metrics`  
- **Go sidecar** — `GET /go/health`, `GET /go/version`, `GET /go/translate?q=…` (stub)

---

## 3) Environment & Build (summary)

**Worker**
- `EDGE_SHIELD_TOKEN`, `EDGE_SHIELD_ENFORCE`, `CORS_ORIGINS`, `BACKEND_CACHE_TTL`, Stripe secrets, `ADMIN_KEY`
- KV namespaces: `CACHE`, `USAGE`

**FastAPI (Fly)**
- `EDGE_SHIELD_TOKEN` (required); optional fallback:  
  `OPENAI_API_KEY`, `ENABLE_GPT_FALLBACK=1`, `GPT_MODEL=gpt-4o-mini`, `GPT_MAX_TOKENS=128`, `GPT_TIMEOUT_MS=2000`

**Go sidecar (Fly)**
- Env: `PORT` (8080), `COMMIT_SHA`, `BUILD_TIME`  
- Build args (in `backend-go/fly.toml`):  
  ```
  [build.args]
    COMMIT_SHA = ""
    BUILD_TIME = ""
    DEPS_SHA   = ""
  ```
- Dockerfile forces deps refresh (`DEPS_SHA`) and runs `go mod tidy` in builder.

---

## 4) One‑Minute Verification (prod)

```bash
# Front door
curl -sI https://dhkalign.com | head -n1
curl -I  https://www.dhkalign.com/test?q=1         # 301 → apex

# Edge + origin
curl -fsS https://edge.dhkalign.com/version | jq
curl -fsS https://backend.dhkalign.com/health | jq

# Free translate (through Edge)
curl -fsS 'https://edge.dhkalign.com/api/translate?q=Rickshaw%20pabo%20na' | jq
```

---

## 5) Dev Quick Tests (local Worker @ 127.0.0.1:8789)

```bash
# Edge health
curl -s http://127.0.0.1:8789/edge/health | jq .

# Admin cache stats
curl -s -H "x-admin-key: <ADMIN_KEY>" http://127.0.0.1:8789/admin/cache_stats | jq .

# Admin key ops
curl -s -H "x-admin-key: <ADMIN_KEY>" "http://127.0.0.1:8789/admin/keys/add?key=newkey123"
curl -s -H "x-admin-key: <ADMIN_KEY>" "http://127.0.0.1:8789/admin/keys/check?key=newkey123"
curl -s -H "x-admin-key: <ADMIN_KEY>" "http://127.0.0.1:8789/admin/keys/del?key=newkey123"

# Free translate — POST (canonical) and GET
curl -sX POST http://127.0.0.1:8789/translate -H 'content-type: application/json' -d '{"text":"Bazar korbo"}' | jq
curl -s    'http://127.0.0.1:8789/translate?q=Bazar%20korbo' | jq

# Edge cache MISS → HIT (check CF-Cache-Edge)
curl -is -X POST http://127.0.0.1:8789/translate -H 'content-type: application/json' -d '{"text":"Bazar korbo"}' | grep CF-Cache-Edge
curl -is -X POST http://127.0.0.1:8789/translate -H 'content-type: application/json' -d '{"text":"Bazar korbo"}' | grep CF-Cache-Edge

# Bypass edge cache (origin TTL cache visible via X-Backend-Cache)
curl -is -X POST "http://127.0.0.1:8789/translate?cache=no" -H 'content-type: application/json' -d '{"text":"Bazar korbo"}' | grep X-Backend-Cache
```

---

## 6) Operator Commands (quick)

**Go app (Fly) — wake/park**
```bash
GO_APP="$(awk -F\" '/^app = /{print $2}' backend-go/fly.toml)"
flyctl scale count 1 -a "$GO_APP" && flyctl status -a "$GO_APP"   # wake
flyctl scale count 0 -a "$GO_APP"                                 # park
```

**Go app — deploy with metadata + deps cache‑bust**
```bash
cd backend-go
COMMIT_SHA="$(git -C .. rev-parse --short HEAD || echo dev)"
BUILD_TIME="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
DEPS_SHA="$(shasum -a 256 go.mod | awk '{print $1}')-$(date +%s)"
flyctl deploy --remote-only -a "$GO_APP" \
  --build-arg COMMIT_SHA="$COMMIT_SHA" \
  --build-arg BUILD_TIME="$BUILD_TIME" \
  --build-arg DEPS_SHA="$DEPS_SHA" \
  --yes
cd -
```

**FastAPI origin (Fly) — deploy**
```bash
API_APP="dhkalign-backend"
cd backend && flyctl deploy --remote-only -a "$API_APP" --yes && cd -
```

**Smoke — trigger on your branch**
```bash
BRANCH="$(git rev-parse --abbrev-ref HEAD)"
gh workflow run ".github/workflows/smoke.yml" -r "$BRANCH"
gh run list --workflow ".github/workflows/smoke.yml" --branch "$BRANCH" -L 1
```

---

## 7) Troubleshooting (cheatsheet)

| Symptom                                   | Cause                                   | Fix |
|-------------------------------------------|-----------------------------------------|-----|
| Edge 5xx / `/version` fails               | Worker outage / WAF rule                | Check Smoke; ensure no WAF rule blocks `/version` |
| Origin 403 (Worker→origin)                | `x‑edge‑shield` mismatch                | Set same token in Worker/Fly; redeploy both |
| Pro 401 via Edge                          | Missing/invalid `x‑api-key`             | Supply valid key; rotate if leaked |
| Always MISS at edge                       | Request mismatch or `?cache=no`         | Send identical method/path/body; drop bypass |
| Stripe webhook 400                        | Bad `stripe-signature` / replay         | Verify secret; ensure KV replay lock present |
| “file is not a database” on origin        | Bad SQLite upload                       | Re‑upload via single‑line pipe; verify rows |
| Billing key endpoint unauthorized         | Request from non‑allowlisted origin     | Ensure request originates from allowlisted IP or Worker |

---

## 8) Notes / Gotchas

- The Worker is the **only** public ingress; all client flows go through edge.  
- Never commit secrets, virtualenv, or DB files; use Wrangler/Fly secrets instead.  
- HMAC‑signed audit logs exclude text and rotate ≤ 90 days.  
- Required checks on `main`: **`Cloudflare Pages`**, **`smoke`** (CodeQL non‑blocking).