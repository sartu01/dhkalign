# DHK Align — Public README

This is the public-facing README for DHK Align.

The full **Secured MVP README** with internal architecture and sensitive details has been moved to `private/docs/README_secured_MVP.md` and is **not intended for public GitHub**.

For general documentation, see [docs/](docs/).
# DHK Align — Banglish ⇄ English Transliterator-tion Engine

> **Open-core, security-first transliterator-tion engine.**  
> Free tier runs client-side with safe data; Pro tier is API-key gated with premium packs.  

---

## 🌟 Overview

- **Frontend:** React SPA (free tier UI, client cache for safe data).
- **Edge Worker:** Cloudflare Worker is the only ingress in prod/dev.  
  - KV namespaces:  
    - `CACHE` — TTL response cache (`CF-Cache-Edge: HIT|MISS`)  
    - `USAGE` — per-API-key counters (40h rolling TTL)  
  - Admin routes: `/edge/health`, `/admin/health`, `/admin/cache_stats`
- **Backend:** FastAPI (private origin, port 8090) behind the Worker.  
  - Routes: `/health`, `/translate`, `/translate/pro`  
  - TTL cache: adds `X-Backend-Cache: HIT|MISS` when bypassing edge cache (`?cache=no`)  
  - Audit: HMAC-signed append-only logs (`private/audit/security.jsonl`)

---

## ⚡ Quick Start (Dev, 2 Tabs)

**Server tab**
```bash
cd ~/Dev/dhkalign
export EDGE_SHIELD_TOKEN="$(cat .secrets/EDGE_SHIELD_TOKEN)" \
  EDGE_SHIELD_ENFORCE=1 BACKEND_CACHE_TTL=180
./scripts/run_server.sh   # backend on http://127.0.0.1:8090
```

**Work tab**
```bash
cd ~/Dev/dhkalign/infra/edge
BROWSER=false wrangler dev --local --port 8788 --config wrangler.toml
# Worker on http://127.0.0.1:8788
```

---

## 🧪 Curl Tests

**Edge health**
```bash
curl -s http://127.0.0.1:8788/edge/health | jq .
```

**Admin cache stats**
```bash
curl -s -H "x-admin-key: $(cat ~/Dev/dhkalign/.secrets/ADMIN_KEY)" \
  http://127.0.0.1:8788/admin/cache_stats | jq .
```

**Cache MISS → HIT**
```bash
curl -is -X POST http://127.0.0.1:8788/translate \
  -H 'Content-Type: application/json' \
  -d '{"text":"kemon acho","src_lang":"banglish","dst_lang":"english"}' | grep CF-Cache-Edge

curl -is -X POST http://127.0.0.1:8788/translate \
  -H 'Content-Type: application/json' \
  -d '{"text":"kemon acho","src_lang":"banglish","dst_lang":"english"}' | grep CF-Cache-Edge
```

**Bypass edge (backend TTL cache)**
```bash
curl -is -X POST "http://127.0.0.1:8788/translate?cache=no" \
  -H 'Content-Type: application/json' \
  -d '{"text":"kemon acho","src_lang":"banglish","dst_lang":"english"}' | grep X-Backend-Cache
```

---

## 🔐 Security Posture

- **Edge shield:** all traffic goes through Cloudflare Worker; origin blocked unless header matches `EDGE_SHIELD_TOKEN`.
- **Pro API:** `/translate/pro` requires `x-api-key`.  
- **Two-layer caching:** edge KV (`CF-Cache-Edge`), backend TTL (`X-Backend-Cache`).  
- **Audit logs:** append-only HMAC JSONL, no user text stored.  
- **Backups:** nightly cron to `private/backups/`.

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

## 📄 License & Contact

MIT License.

- Info: [info@dhkalign.com](mailto:info@dhkalign.com)  
- Security: [admin@dhkalign.com](mailto:admin@dhkalign.com)  