# DHK Align — Security Policy (October 2025)

This document states the deployed security model for DHK Align. It aligns with `README.md`, `docs/ARCHITECTURE.md`, `docs/SECURITY_RUNBOOK.md`, and `docs/PROPERTY_DEFENSE.md`.

---
## 1) Scope & Principles
- **Edge‑only ingress:** Clients call the **Cloudflare Worker**. Only the Worker calls the private origin with the **internal** header `x-edge-shield`. Clients never send this header.
- **Least privilege:** Keys/roles are scoped; secrets never in git. 
- **Defense in depth:** Edge quotas + origin rate limits; KV replay locks; strict webhook validation; CORS/CSP; JSON‑only errors.
- **Data minimization:** No user text stored in long‑term logs. DB holds curated phrases + auto‑learned GPT misses.

---
## 2) Authentication & Authorization

### Truth table (client surface)
| Surface (client calls)    | `x-edge-shield` | `x-api-key` | `x-admin-key` |
|---------------------------|----------------:|------------:|--------------:|
| Edge `/translate` (free)  | No              | No          | No            |
| Edge `/translate/pro`     | No              | **Yes**     | No            |
| Edge `/admin/keys/*`      | No              | No          | **Yes**       |

> **Origin is private.** The Worker injects `x-edge-shield:<token>` when calling the origin. Clients never send `x-edge-shield`.

### Keys
- **Admin key:** required on `/admin/*`; stored as Wrangler secret (prod) or `.dev.vars` (dev).
- **API key (Pro):** stored in KV as `apikey:<key> = "1"`, metadata at `apikey.meta:<key>`.
- **Stripe‑minted keys:** `/webhook/stripe` mints, `/billing/key?session_id=…` returns **once**; origin‑allowlisted.

---
## 3) Edge Worker Security (Cloudflare)
- **Quotas:** KV daily per‑API‑key quota (e.g., 1000/day) → `429 quota_exceeded`.
- **KV namespaces:**
  - `CACHE` — response cache; header `CF-Cache-Edge: HIT|MISS`.
  - `USAGE` — counters, replay locks, API key store.
- **CORS:** allowlist domains only (prod: `dhkalign.com`, `www.dhkalign.com`; dev: `127.0.0.1:5173`).
- **Admin routes:** `/admin/health`, `/admin/cache_stats`, `/admin/keys/add|check|del` (GET `?key=…` and optional POST JSON if enabled).
- **Billing handoff:** `/billing/key?session_id=…` returns key once; then mapping is deleted.

---
## 4) Backend Security (Fly.io FastAPI)
- **Shield enforcement:** requests must include valid `x-edge-shield` (set by Worker).
- **Routes:** `/health`, `/translate` (free), `/translate/pro` (Pro), `/metrics` (Prometheus).
- **JSON‑only errors:** `{ ok:false, error:"…" }`; never HTML error bodies.
- **Rate limits:** IP‑level SlowAPI (60/min) when enabled on `/translate*`.
- **Caching:**
  - Bypass edge via `?cache=no` → backend adds `X-Backend-Cache: HIT|MISS`.
- **Data identity:** uniqueness on `(src_lang, roman_bn_norm, tgt_lang, pack)`; `id` is cosmetic; DB path `backend/data/translations.db`.

---
## 5) Stripe Webhook Security
- **Endpoint:** Worker `/webhook/stripe`.
- **Requirements:** `stripe-signature` header; **5‑minute tolerance**; only `checkout.session.completed` accepted.
- **Replay lock:** KV `stripe_evt:<event_id>` (~90 days). 
- **Key mint:** sets `apikey:<key>="1"`, `apikey.meta:<key>`; maps `session_to_key:<session_id>` (7‑day TTL). 
- **Do not echo keys** to Stripe response. Clients fetch via `/billing/key`.

---
## 6) GPT Fallback (Optional, Pro only)
- **Flow:** DB‑first → on miss, call model → auto‑insert into DB (pack=`auto`, safety=2) → serve.
- **Model:** default `gpt-4o-mini` (cheap, smart). 
- **Controls:** `OPENAI_API_KEY`, `ENABLE_GPT_FALLBACK=1`, `GPT_MODEL`, `GPT_MAX_TOKENS` (default 128), `GPT_TIMEOUT_MS` (default 2000). 
- **Observability:** metrics counters `dhk_db_hit_total`, `dhk_gpt_fallback_total`, `dhk_gpt_fail_total`, `dhk_request_latency_seconds`.

---
## 7) CSP / CORS

### CSP (prod example)
```html
<meta http-equiv="Content-Security-Policy" content="
  default-src 'self';
  script-src 'self' https://js.stripe.com 'nonce-__NONCE__';
  style-src 'self' 'nonce-__NONCE__';
  img-src 'self' data: https:;
  connect-src 'self' https://<YOUR-WORKER-PROD-HOST> https://backend.dhkalign.com;
  frame-src https://js.stripe.com;
  object-src 'none'; base-uri 'self'; upgrade-insecure-requests">
```

### CSP (dev additions)
Add `http://127.0.0.1:5173` and `http://127.0.0.1:8789` to `connect-src`. Prefer nonce over SRI for `js.stripe.com` (URL revs frequently).

### CORS allowlist
- Prod: `https://dhkalign.com`, `https://www.dhkalign.com`
- Dev: `http://127.0.0.1:5173`

---
## 8) Secrets & Environments
- **Worker (prod):** Wrangler secrets — `ADMIN_KEY`, `EDGE_SHIELD_TOKEN`, `STRIPE_WEBHOOK_SECRET`.
- **Worker (dev):** `infra/edge/.dev.vars` (do not commit).
- **Backend (Fly):** `OPENAI_API_KEY`, `ENABLE_GPT_FALLBACK`, `GPT_MODEL`, `GPT_MAX_TOKENS`, `GPT_TIMEOUT_MS`, `DEBUG_FALLBACK` (0/1).

---
## 9) Troubleshooting
| Symptom | Likely Cause | Fix |
|---|---|---|
| 401 on `/admin/keys/*` | Wrong `x-admin-key` | Set correct prod ADMIN_KEY via `wrangler secret put` and redeploy |
| 401 `invalid api key` (Pro) | KV missing `apikey:<key>` | Mint key via `/admin/keys/add?key=…` |
| 403/401 at origin | Missing `x-edge-shield` | Worker must inject shield; set correct secret in both Worker + backend |
| Stripe signature fail | Wrong `whsec_*` or clock skew | Update secret; ensure 5‑minute tolerance |
| Fallback never triggers | `ENABLE_GPT_FALLBACK=0` or missing `OPENAI_API_KEY` | Set Fly secrets and redeploy |

---
## 10) Incident Runbooks (pointers)
- **Security Runbook:** `docs/SECURITY_RUNBOOK.md` — shield failures, Stripe replay, key abuse, GPT cost spikes.
- **Property Defense:** `docs/PROPERTY_DEFENSE.md` — abuse taxonomy, takedown flow, evidence collection.

---
## 11) License & Contacts
- **Code:** MIT (`LICENSE_CODE.md`). **Data:** Proprietary (`LICENSE_DATA.md`).
- Security/Ops: **admin@dhkalign.com**  
- Info: **info@dhkalign.com**