# DHK Align — Backend (FastAPI)

Private FastAPI origin that sits **behind the Cloudflare Worker**.  
Exposes the secured translation API used by DHK Align and optional analytics/feedback if enabled.  
**Do not expose this origin directly on the public internet.**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.11x-009688.svg)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](../LICENSE)

---

## What this service does

- **/translate** (Free tier) — serves **safety ≤ 1** packs (safe/cultural)
- **/translate/pro** (Pro, header `x-api-key`) — serves **safety ≥ 2** packs (slang/profanity/dialect)
- **/health** — health + basic counters
- Optional: **analytics** and **feedback** capture (privacy‑preserving)

> All client traffic must go through the **Edge Worker**. The Worker adds security headers, CORS, rate limits, and `x-edge-shield` to authenticate requests to this origin.

---

## Quick start (local)

```bash
# repo root
cd ~/Dev/dhkalign

# create venv & install
python3 -m venv backend/.venv
source backend/.venv/bin/activate   # Windows: backend\\.venv\\Scripts\\activate
pip install -r backend/requirements.txt

# env
cp backend/.env.example backend/.env

# run (dev)
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8090

# health
curl -s http://127.0.0.1:8090/health | jq .
```

**Two‑tab discipline (recommended)**
- **Server tab:** run the FastAPI dev server as above.
- **Edge tab:** from `infra/edge`, run `wrangler dev …` so the browser always talks to the Worker.

---

## Endpoints

| Route                   | Method | Auth                                   | Purpose                                  |
|-------------------------|--------|----------------------------------------|------------------------------------------|
| `/health`               | GET    | none                                   | API status `{ ok, db, safe_rows }`       |
| `/version`              | GET    | none                                   | build/version info                        |
| `/translate`            | POST   | none                                   | Free tier (safety ≤ 1)                    |
| `/translate/pro`        | POST   | `x-api-key`                            | Pro tier (safety ≥ 2)                     |
| `/metrics`              | GET    | `x-edge-shield` + Edge allowlist       | Prometheus metrics (optional)             |
| `/docs`, `/redoc`       | GET    | none                                   | Interactive OpenAPI docs                  |

**Bodies**
```json
// /translate
{ "q": "kemon acho", "src_lang": "bn-rom", "tgt_lang": "en" }

// /translate/pro
{ "q": "Bindaas", "src_lang": "bn-rom", "tgt_lang": "en" }
```

**Common errors:** `400` malformed, `413` > 2KB, `415` content-type, `401` missing/invalid API key, `429` rate limited.

---

## Environment

Create `backend/.env`:
```ini
# CORS (comma‑separated)
CORS_ORIGINS=http://localhost:3000,https://dhkalign.com,https://www.dhkalign.com

# Pro auth
API_KEYS=<hex_or_comma_separated_hexes>

# Edge shield (Worker → origin)
EDGE_SHIELD_ENFORCE=1
EDGE_SHIELD_TOKEN=<hex>

# Optional DB (for feedback/analytics persistence)
DATABASE_URL=sqlite:///./backend/data/dhkalign.db

# Logging
LOG_LEVEL=INFO
LOG_DIR=backend/logs

# Caches / rate limit
BACKEND_CACHE_TTL=180
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=60
RATE_LIMIT_WINDOW=60
```

---

## Security (implemented)

- Strict JSON schema (`q` required, ≤ 1000 chars); 2KB POST body cap
- Sanitization (strip SQL‑like tokens, traversal)
- **CORS allowlist** from `CORS_ORIGINS`
- Security headers (`Content-Security-Policy`, `Strict-Transport-Security`, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`)
- IP + fingerprint rate limiting (60/min), temp bans after abuse
- `x-api-key` on `/translate/pro`
- **HMAC‑signed audit logs** (append‑only) at `private/audit/security.jsonl`

---

## Project structure

```
backend/
├─ app/
│  ├─ api/
│  │  ├─ routes/
│  │  │  ├─ translate.py
│  │  │  ├─ feedback.py
│  │  │  └─ health.py
│  │  └─ deps.py
│  ├─ core/            # config, logging
│  ├─ models/          # pydantic models
│  └─ utils/           # helpers (logger, metrics)
├─ data/               # SQLite (git‑ignored)
├─ logs/               # JSONL logs (git‑ignored)
├─ scripts/            # run_server.sh, backups, normalize/import/export
├─ requirements.txt
├─ main.py
└─ README.md
```

---

## Docker (optional)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
EXPOSE 8090
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8090"]
```

```bash
docker build -t dhkalign-backend .
docker run -d -p 8090:8090 --name dhkalign-backend \
  -e EDGE_SHIELD_ENFORCE=1 -e EDGE_SHIELD_TOKEN=... \
  -e CORS_ORIGINS=https://dhkalign.com \
  dhkalign-backend
```

---

## One‑minute verification

```bash
# dev server
curl -s http://127.0.0.1:8090/health | jq .

# through Edge (adjust port for your wrangler dev)
PORT=8789
curl -s http://127.0.0.1:$PORT/edge/health | jq .
```

---

## Notes

- Keep this origin **private** (Tunnel/orange cloud); only the Worker should call it.
- Never commit secrets, `.env`, DB files, or anything under `private/`.
- Export a safe client cache with `backend/scripts/export_client_cache.py` (populates `frontend/src/data/dhk_align_client.json`).

---

## License / Contacts

MIT — see `LICENSE`.  
Support — info@dhkalign.com • Security — admin@dhkalign.com