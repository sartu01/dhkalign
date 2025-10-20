# DHK Align — Public README (Oct 2025)

**DHK Align** is an open‑core, security‑first Banglish ⇄ English translation engine with a hardened **Cloudflare Edge** and two origins on **Fly.io** (Python FastAPI in prod, Go sidecar for parity). Frontend is a Cloudflare Pages SPA.

---

## Stack at a glance

- **Edge (Cloudflare Worker)**
  - Routes: `GET /edge/health`, `GET /version`, `GET /api/translate?q=…` (free), `POST /translate` (free, JSON), `POST /translate/pro` (Pro, `x-api-key`, GPT fallback + DB backfill).
  - Hardened: strict CORS (apex/www + localhost in dev), CSP/HSTS/Referrer‑Policy/X‑Content‑Type‑Options/Permissions‑Policy, sanitized 5xx. Stripe webhook exempt from Edge‑Shield; signature verified at origin.
- **Origins (Fly.io)**
  - **FastAPI (prod)**: `GET /health`, `GET /version`, DB lookups, GPT‑4o‑mini fallback (optional), metrics, audit.
  - **Go sidecar (parity pilot)**: `GET /go/health`, `GET /go/version`, `GET /go/translate?q=…` (stub echo). Deployed and **parked (scale=0)** by default.
- **Frontend (Cloudflare Pages)**: SPA; output `frontend/dist/`. `_headers` and `_redirects` in place; SPA fallback `/* /index.html 200`.
- **Data**: SQLite (low‑cost). Future: Litestream S3 backup.
- **CI / Protections**
  - Required checks on `main`: **`Cloudflare Pages`** and **`smoke`** (speed mode). CodeQL runs but is **not** required.
  - **Smoke** validates apex/redirects, Edge `/version`, backend health (tolerant), Go sidecar health (non‑blocking, host auto‑derived from `backend-go/fly.toml`), free translate (tolerant).

---

## Quick Start (Development)

**Prereqs**: Python ≥ 3.11, Node ≥ 18, `jq`, `sqlite3`, `cloudflared`, `wrangler`, `gh` (GitHub CLI), `flyctl`.

### Backend (FastAPI) + Worker (local)
```bash
# repo root
cd ~/Dev/dhkalign

# run FastAPI (uses PORT=8090)
export EDGE_SHIELD_TOKEN="$(grep -m1 '^EDGE_SHIELD_TOKEN=' infra/edge/.dev.vars | cut -d= -f2)" \
       EDGE_SHIELD_ENFORCE=1 BACKEND_CACHE_TTL=180
./scripts/run_server.sh    # http://127.0.0.1:8090

# run Worker (dev)
cd infra/edge
BROWSER=false wrangler dev --local --ip 127.0.0.1 --port 8789 --config wrangler.toml
# http://127.0.0.1:8789
```

### Go sidecar (Fly.io) — build & deploy

The app name is stored in `backend-go/fly.toml` (`app = "<name>"`). Your **Personal** org slug is `personal`.

```bash
cd ~/Dev/dhkalign/backend-go
APP="$(awk -F\" '/^app = /{print $2}' fly.toml)"; ORG="personal"
flyctl auth whoami >/dev/null 2>&1 || flyctl auth login
# create if missing
flyctl apps list | awk -v a="$APP" '$1==a{f=1} END{exit !f}' || flyctl apps create "$APP" -o "$ORG" --yes

# build metadata + deps cache-bust (forces fresh go.mod/go.sum resolution on remote builder)
COMMIT_SHA="$(git -C .. rev-parse --short HEAD 2>/dev/null || echo dev)"
BUILD_TIME="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
DEPS_SHA="$(shasum -a 256 go.mod | awk '{print $1}')-$(date +%s)"

flyctl deploy --remote-only -a "$APP" \
  --build-arg COMMIT_SHA="$COMMIT_SHA" \
  --build-arg BUILD_TIME="$BUILD_TIME" \
  --build-arg DEPS_SHA="$DEPS_SHA" \
  --yes

# sanity
URL="https://$APP.fly.dev"
curl -fsS "$URL/go/health"    | jq .
curl -fsS "$URL/go/version"   | jq .
curl -fsS "$URL/go/translate?q=Rickshaw%20pabo%20na" | jq .

# cost guard (park when idle)
flyctl scale count 0 -a "$APP"
```

---

## One‑minute verification (prod)

```bash
# front door
curl -sI https://dhkalign.com | head -n1
curl -I "https://www.dhkalign.com/test?q=1"   # expect 301 → apex

# edge + backend
curl -fsS https://edge.dhkalign.com/version | jq
curl -fsS https://backend.dhkalign.com/health | jq

# free translate
curl -fsS 'https://edge.dhkalign.com/api/translate?q=Rickshaw%20pabo%20na' | jq
# POST (JSON)
curl -fsS -X POST 'https://edge.dhkalign.com/translate' -H 'content-type: application/json' -d '{"q":"Rickshaw pabo na"}' | jq
```

---

## Security

- **Edge‑Shield**: Worker authenticates to origin via `x-edge-shield` secret; clients never send it.
- **Security headers**: `Content-Security-Policy`, `Strict-Transport-Security`, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`.
- **Cache headers**: `CF-Cache-Edge: HIT|MISS` at edge; `X-Backend-Cache: HIT|MISS` when edge is bypassed.
- **Pro auth**: `x-api-key` on `/translate/pro`; admin: `x-admin-key`.
- **Rate limits**: IP + key quotas at edge; backend sliding windows.
- **Audit**: append‑only, HMAC‑signed; no user text stored.
- **Stripe**: webhook signature verify + replay protection.
- **CORS**: strict allowlist.

---

## Environment Variables

**Worker**
- `EDGE_SHIELD_TOKEN`, `EDGE_SHIELD_ENFORCE`, `CORS_ORIGINS`

**Backend (FastAPI / Fly)**
- `OPENAI_API_KEY` (if GPT fallback on), `ENABLE_GPT_FALLBACK=1`, `GPT_MODEL=gpt-4o-mini`, `GPT_MAX_TOKENS=128`, `GPT_TIMEOUT_MS=2000`

**Go sidecar**
- `PORT` (default `8080`), `COMMIT_SHA`, `BUILD_TIME`

---

## Endpoints

**Edge**
- `GET /edge/health`, `GET /version`
- `GET /api/translate?q=…` (free)
- `POST /translate` (free, JSON)
- `POST /translate/pro` (Pro, `x-api-key`)

**FastAPI**
- `GET /health`, `GET /version`

**Go (parity)**
- `GET /go/health`, `GET /go/version`, `GET /go/translate?q=…` (stub)

---

## CI / Branch Protection

- Required on `main`: `["Cloudflare Pages","smoke"]`
- **Smoke**: apex 200; `www` → apex 301; Edge `/version` tolerant; backend health tolerant + Fly fallback; Go sidecar health (non‑blocking, host auto‑derived); free translate GET+POST (tolerant).
- Trigger on your branch:
  ```bash
  gh workflow run ".github/workflows/smoke.yml" -r "$(git rev-parse --abbrev-ref HEAD)"
  ```

---

## Roadmap

- Implement real `/go/translate` (DB + caching), then partial routing from Worker for parity tests.
- Stripe UI on Pages: add CSP to allow `js.stripe.com` and `hooks.stripe.com`; host Apple Pay association file.
- Vite migration PR (no traffic switch; build to `frontend/dist/`).
- Scraping pipeline (colly/chromedp) with SQLite ingest and validators.

---

## Contact

- Info: [info@dhkalign.com](mailto:info@dhkalign.com)  
- Security: [admin@dhkalign.com](mailto:admin@dhkalign.com)

---

© 2025 DHK Align. Code under MIT; data proprietary.