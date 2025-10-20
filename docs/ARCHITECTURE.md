# DHK Align — Architecture (Oct 2025)

**Open‑core, security‑first Banglish ⇄ English translation engine** with a hardened **Cloudflare Edge** and two origins on **Fly.io**. Frontend is a Cloudflare Pages SPA.

---

## 1) Components (at a glance)

- **Frontend (Cloudflare Pages)**
  - SPA UI (CRA today → Vite soon), build output `frontend/build` (→ `frontend/dist` after Vite).
  - Talks **only** to the Edge Worker.

- **Edge Worker (Cloudflare Worker) — single public ingress**
  - Routes:  
    `GET /edge/health`, `GET /version`, `GET /api/translate?q=…` (free), `POST /translate` (free, JSON), `POST /translate/pro` (Pro, `x-api-key`)  
    Admin: `/admin/*` (keys, whoami, cache stats), Billing: `/billing/key?session_id=…`, Stripe: `/webhook/stripe`
  - **Shielding**: adds `x-edge-shield` when calling origins; clients never see it.
  - **Security**: strict CORS; `Content-Security-Policy`, `Strict-Transport-Security`, `Referrer-Policy`, `X-Content-Type-Options`, `X-Frame-Options`, `Permissions-Policy`; sanitized 5xx.
  - **Abuse guard**: per‑IP/per‑key sliding windows; daily quotas in KV.
  - **Caching**: edge KV (`CACHE`) with `CF-Cache-Edge: HIT|MISS`; `?cache=no` bypasses edge.

- **Origins (Fly.io) — private behind Edge**
  - **FastAPI (prod)**: `/health`, `/version`, `/translate`, `/translate/pro`, `/metrics`. DB‑first; optional GPT fallback inserts to DB on miss. Expects `x-edge-shield` from Edge.
  - **Go sidecar (parity pilot)**: `/go/health`, `/go/version`, `/go/translate` (stub echo). Deployed; **parked** (scale 0) by default; used for parity & future cutover.

- **Data**
  - SQLite at `backend/data/translations.db`. Safety ≤ 1 = free, ≥ 2 = pro packs.  
    Future: Litestream S3 for backups.

- **CI / Protections**
  - Required checks on `main`: **`Cloudflare Pages`** and **`smoke`** (speed mode).  
    `smoke` validates apex/redirects, Edge `/version`, backend health (tolerant), Go health (non‑blocking, host auto‑derived), and free translate (tolerant).

---

## 2) Request flow

```
React SPA (browser)
    ↓  (HTTPS)
Cloudflare Worker (Edge)  — CORS, headers, quotas, cache, routing
    ↓  (adds x-edge-shield)
Fly.io FastAPI (origin)   — DB-first; optional GPT fallback → DB
    ↓
SQLite (packs)            — safety tiers; packs incl. slang/profanity/dialect
```

Notes:
- Pro requests include `x-api-key` to Edge; Edge authenticates to origin with `x-edge-shield`.
- Edge caches successful responses; backend exposes `X-Backend-Cache: HIT|MISS` when edge bypassed.

---

## 3) Endpoints (public surfaces)

**Edge**
- `GET /edge/health` — edge health
- `GET /version` — build SHA
- `GET /api/translate?q=…` — free path (DB‑first)
- `POST /translate` — free (JSON)
- `POST /translate/pro` — key‑gated (Pro packs); JSON body canonical

**Origin (FastAPI, private)**
- `GET /health`, `GET /version`, `POST /translate`, `POST /translate/pro`, `GET /metrics`

**Go sidecar (parity)**
- `GET /go/health`, `GET /go/version`, `GET /go/translate?q=…` (stub)

---

## 4) Security posture

| Surface (client calls)          | `x-edge-shield` | `x-api-key` | `x-admin-key` |
|--------------------------------|----------------:|------------:|--------------:|
| Edge `/api/translate` (free GET) | No              | No          | No            |
| Edge `POST /translate` (free POST) | No            | No          | No            |
| Edge `/translate/pro`           | No              | **Yes**     | No            |
| Edge `/admin/*`                 | No              | No          | **Yes**       |
| Origin (FastAPI)                | **Yes** (Edge)  | Optional    | Optional      |

- Only the **Worker** calls origins; clients never send `x-edge-shield`.
- Strict CORS; quotas per key; IP guardrails; audit logs (HMAC‑signed).
- Stripe webhook requires `stripe-signature`; KV replay lock.

---

## 5) Observability & metrics

- FastAPI exports Prometheus metrics: `dhk_db_hit_total`, `dhk_gpt_fallback_total`, `dhk_gpt_fail_total`, request latency, etc.
- Smoke (CI) exercises key surfaces and dumps bodies on failure for fast triage.

---

## 6) One‑minute verification

```bash
# front door
curl -sI https://dhkalign.com | head -n1
curl -I "https://www.dhkalign.com/test?q=1"   # 301 → apex

# edge + backend
curl -fsS https://edge.dhkalign.com/version | jq
curl -fsS https://backend.dhkalign.com/health | jq

# free translate (through edge)
curl -fsS 'https://edge.dhkalign.com/api/translate?q=Rickshaw%20pabo%20na' | jq
# free translate (POST through edge)
curl -fsS -X POST 'https://edge.dhkalign.com/translate' \
  -H 'content-type: application/json' -d '{"q":"Rickshaw pabo na"}' | jq
```

---

## 7) Environment (summary)

**Worker**: `EDGE_SHIELD_TOKEN`, `EDGE_SHIELD_ENFORCE`, `CORS_ORIGINS`, Stripe secrets, admin/pro keys.  
**FastAPI**: `EDGE_SHIELD_TOKEN`, `OPENAI_API_KEY` (optional fallback), `ENABLE_GPT_FALLBACK=1`, `GPT_MODEL`, `GPT_MAX_TOKENS`, `GPT_TIMEOUT_MS`, `BACKEND_CACHE_TTL`, `CORS_ORIGINS`.  
**Go**: `PORT` (8080), `COMMIT_SHA`, `BUILD_TIME`.

---

## 8) Roadmap (near‑term)

- Implement real `/go/translate` (DB + caching), add Edge flag to route a small % to Go for parity.
- Vite migration (build to `frontend/dist`; Pages config update).
- Stripe UI on Pages (CSP allowlist; Apple Pay association).
- Litestream backups for SQLite.