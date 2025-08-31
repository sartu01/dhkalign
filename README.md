# DHK Align — Banglish ⇄ English Transliterator‑tion (Secured MVP)

[![Status](https://img.shields.io/badge/state-secured_MVP-0b7.svg)](#)
[![FastAPI](https://img.shields.io/badge/FastAPI-≥0.111-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.x-00d8ff.svg)](https://react.dev/)
[![Security](https://img.shields.io/badge/security-defense_in_depth-cd2f2e.svg)](docs/SECURITY.md)

A **security‑first**, culturally‑aware transliterator‑tion engine for **Banglish (Bengali in Roman script) ⇄ English**.  
The app now runs with a **Free (safe) API** and a **Pro (gated) API** backed by a local SQLite datastore.

- **Free**: `/translate` serves **safety_level ≤ 1** (safe) entries, with a client cache for speed.
- **Pro**: `/translate/pro` serves **safety_level ≥ 2** packs (slang / profanity / dialects) with an **API key**.
- **Defense‑in‑depth**: strict middleware (schema, size caps, CORS, headers), dual rate‑limits, and HMAC audit logs.

---

## 🌟 What’s Live

- **Endpoints**: `GET /health`, `POST /translate`, `POST /translate/pro` (API key)
- **Data split**: `safety_level ≤ 1` (free) vs `≥ 2` (pro) with packs:
  - `slang`, `profanity`, `dialect-sylheti`
- **Security**: input validation & sanitization, **2KB** payload cap, CORS allowlist, security headers, IP+fingerprint rate‑limit, temp bans, **HMAC‑signed** audit logs
- **Ops**: one‑liner server script, nightly cron backups

---

## 🏗️ Current Architecture (repo truth)

```
dhkalign/
├─ backend/                     # FastAPI app (SQLite source of truth)
│  ├─ app_sqlite.py             # API app (health, /translate, mounts pro router)
│  ├─ pro_routes.py             # /translate/pro (API key gated; packs/tiers)
│  ├─ security_middleware.py    # schema checks, CORS, headers, RL, audit hooks
│  ├─ data/
│  │  └─ translations.db        # SQLite DB (safe + pro rows)
│  ├─ scripts/
│  │  ├─ normalize_jsonl.py     # make raw JSONL → CLEAN.jsonl
│  │  ├─ import_clean_jsonl.py  # load CLEAN.jsonl → SQLite (upsert)
│  │  ├─ export_client_cache.py # SQLite → frontend cache (safety ≤ 1)
│  │  └─ secure_log.py          # HMAC append‑only audit logger
├─ frontend/                    # React SPA (optional client cache)
│  └─ src/data/dhk_align_client.json  # generated safe cache
├─ private/                     # 🔒 packs and drafts (not tracked)
│  ├─ packs_raw/newstuff/       # drafts & CLEAN files (safe/pro)
│  └─ pro_packs/{slang,profanity,youth_culture}/
├─ scripts/
│  ├─ run_server.sh             # start uvicorn with env + sane reload
│  └─ backup_db.sh              # nightly DB backup (used by cron)
├─ gateway/                     # Cloudflare Worker (edge shield; planned)
│  ├─ worker.js
│  └─ wrangler.toml
├─ docs/
│  ├─ SECURITY.md               # high‑level posture (edge + origin)
│  └─ NEXT_TODO.md              # iron‑clad next steps
└─ README.md
```

---

## 🚀 Quick Start (Local)

> **Prereq**: macOS + Python 3.11+ + Node 18+; repo located at `~/Dev/dhkalign`

**Start API (server tab):**
```bash
cd ~/Dev/dhkalign
./scripts/run_server.sh
```

**Health (work tab):**
```bash
curl -s http://127.0.0.1:8090/health | jq .
# {"ok":true,"db":".../backend/data/translations.db","safe_rows":446}
```

**Free translate (work tab):**
```bash
curl -s -X POST http://127.0.0.1:8090/translate \
  -H "Content-Type: application/json" \
  -d '{"text":"kemon acho","src_lang":"banglish","dst_lang":"english"}' | jq .
```

**Pro translate (API key)**
```bash
KEY=$(grep '^API_KEYS=' backend/.env | cut -d= -f2)
PHRASE=$(sed -n '1p' private/pro_packs/slang/dhk_align_slang_pack_002.CLEAN.jsonl | jq -r .banglish)
curl -s -X POST http://127.0.0.1:8090/translate/pro \
  -H "Content-Type: application/json" -H "x-api-key: $KEY" \
  -d "{\"text\":\"$PHRASE\",\"pack\":\"slang\"}" | jq .
```

---

## 🔑 Environment (`backend/.env`)

```
CORS_ORIGINS=http://localhost:3000,https://dhkalign.com
API_KEYS=<hex>                 # internal key(s) for /translate/pro
AUDIT_HMAC_SECRET=<hex>       # HMAC for append‑only audit logs
```

The app auto‑loads `.env` (via `python-dotenv`), so you don’t need `--env-file` in dev.

---

## 🔒 Security & Ops (implemented)

**Origin middleware**  
- Strict JSON schema (`text` required, ≤1000 chars)  
- Sanitization (strip SQL‑ish tokens, path traversal), **2KB** POST limit  
- CORS allowlist, **security headers** (HSTS/CSP/nosniff/frame‑deny/referrer)  
- IP + fingerprint (UA/Accept/Language) **rate‑limit** (60/min), temp bans after 5 bad  
- **API key** required on `/translate/pro`

**Audit**  
- **HMAC‑signed** append‑only JSONL at `private/audit/security.jsonl`  
- Logged events: `bad_request`, `auth_fail`, `rate_limited`, `cors_block`, `temp_ban_*`

**Backups**  
- Nightly cron (2:05 AM): `./scripts/backup_db.sh` → `private/backups/YYYY-MM-DD_translations.db`

**Edge shield (planned)**  
- Cloudflare Worker + KV minute‑bucket rate limiting; origin hidden behind CF  
- Allowlist paths: `/health`, `/translate`, `/translate/pro`

---

## 🧠 Data & Packs

- **safety_level ≤ 1** → exposed to Free API and client cache  
- **safety_level ≥ 2** → available via Pro API (key required)  
- Packs in use: `slang`, `profanity`, `dialect-sylheti`

**Importing packs**  
```bash
# Normalize raw → CLEAN
python3 backend/scripts/normalize_jsonl.py private/packs_raw/newstuff/dhk_align_cultural_pack_001.jsonl \
  private/packs_raw/newstuff/dhk_align_cultural_pack_001.CLEAN.jsonl cultural 1

# Import CLEAN → SQLite
python3 backend/scripts/import_clean_jsonl.py private/packs_raw/newstuff/dhk_align_cultural_pack_001.CLEAN.jsonl
```

**Export safe client cache**  
```bash
python3 backend/scripts/export_client_cache.py
# writes frontend/src/data/dhk_align_client.json (safety ≤ 1 only)
```

---

## 📡 API Reference (local)

**GET `/health`** → `{ ok:boolean, db:string, safe_rows:number }`

**POST `/translate`** (Free)  
`Content-Type: application/json`  
```json
{ "text": "kemon acho", "src_lang": "banglish", "dst_lang": "english" }
```

**POST `/translate/pro`** (Pro)  
Headers: `x-api-key: <hex>`  
Body: `{ "text": "...", "pack": "slang|profanity|dialect-sylheti" }`

Rate‑limits apply; wrong content-type/oversized/malformed JSON returns **415/413/400**.

---

## 🧩 Development

**Venv** is at `backend/.venv`. VS Code workspace setting should use:  
`python.defaultInterpreterPath = ${workspaceFolder}/backend/.venv/bin/python`

**Helpers**
```bash
./scripts/run_server.sh   # start uvicorn with sane reload + env
./scripts/backup_db.sh    # make a dated SQLite backup
```

---

## 🗺️ Roadmap

- **Edge**: publish Cloudflare Worker + KV (rate‑limit + origin shield)
- **Cache**: in‑process TTL for API responses (reduce repeat DB hits)
- **Admin**: `/admin/health` with metrics (requests, cache hit rate, threats blocked)
- **Guard**: GPT fallback with prompt‑injection checks + token/day caps (Pro only)
- **Quotas**: per‑key usage counters + rotation (KV/SQLite)

---

## 📄 License & Support

MIT – see `LICENSE`.

- General: **info@dhkalign.com**  
- Admin/Security: **admin@dhkalign.com** (subject “SECURITY”)

---

<div align="center">
  <h3>Built for the Bengali community — the first Transliterator‑tion, secured by design.</h3>
</div>