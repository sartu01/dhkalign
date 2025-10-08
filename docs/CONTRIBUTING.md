# DHK Align — Contributing Guide

This guide explains how to run DHK Align locally, maintain security, contribute code/data safely, and perform checks before opening a PR.

---

## 🔒 Ground Rules
- **Ingress:** Clients access the **Cloudflare Worker**; only the Worker calls the private origin with header `x-edge-shield`. Clients never send this header.
- **Secrets:** Dev secrets in `infra/edge/.dev.vars`; prod secrets via Wrangler. **Never** commit secrets to git.
- **Admin:** All `/admin/*` endpoints require `x-admin-key`.
- **JSON contract:** Responses are `{ ok:true, data:{...} }` or `{ ok:false, error:"..." }`. No HTML errors.
- **DB:** Runtime DB at `backend/data/translations.db`.
- **Identity:** Unique DB key on *(src_lang, roman_bn_norm, tgt_lang, pack)*; `id` is cosmetic.
- **Pro fallback (optional):** Origin can call GPT model on DB miss (default `gpt-4o-mini`), auto-inserting results. Controlled via Fly secrets.

---

## ⚡ Quick Start (Dev, 2 Tabs)

**Prerequisites:** Python ≥ 3.11, Node ≥ 18, `jq`, `sqlite3`, `cloudflared`, `wrangler`

**Server tab**
```bash
cd ~/Dev/dhkalign
export EDGE_SHIELD_TOKEN="$(grep -m1 '^EDGE_SHIELD_TOKEN=' infra/edge/.dev.vars | cut -d= -f2)" \
  EDGE_SHIELD_ENFORCE=1 BACKEND_CACHE_TTL=180
./scripts/run_server.sh   # backend at http://127.0.0.1:8090
```
(Alternative: `./scripts/server_up.sh`)

**Work tab (Edge)**
```bash
cd ~/Dev/dhkalign/infra/edge
BROWSER=false wrangler dev --local --ip 127.0.0.1 --port 8789 --config wrangler.toml
# dev Worker at http://127.0.0.1:8789
```

**Secrets**
- Dev: `infra/edge/.dev.vars`  
- Prod: Wrangler secrets

### Backend (Fly) Environment Variables
- `OPENAI_API_KEY` — OpenAI key (sk-…), required if fallback enabled
- `ENABLE_GPT_FALLBACK` — set `1` to enable GPT fallback on DB miss
- `GPT_MODEL` — model name (default: `gpt-4o-mini`)
- `GPT_MAX_TOKENS` — max tokens for fallback (default: `128`)
- `GPT_TIMEOUT_MS` — timeout in ms (default: `2000`)

---

## 🤖 GPT Fallback (optional)

Enable GPT fallback in production to return model translations on DB misses, auto-inserting for future requests:

```bash
flyctl secrets set -a dhkalign-backend \
  OPENAI_API_KEY='sk-…' \
  ENABLE_GPT_FALLBACK='1' \
  GPT_MODEL='gpt-4o-mini' \
  GPT_MAX_TOKENS='128' \
  GPT_TIMEOUT_MS='2000'
cd ~/Dev/dhkalign && flyctl deploy -a dhkalign-backend
```

First miss via `/translate/pro` returns `{ ok:true, data:{ …, "source":"gpt" } }`; subsequent calls return `{ …, "source":"db" }`.

---

## 🧪 Curl Tests

**Edge health**
```bash
curl -s http://127.0.0.1:8789/edge/health | jq .
```

**Admin cache stats (locked)**
```bash
AK=$(grep -m1 '^ADMIN_KEY=' infra/edge/.dev.vars | cut -d= -f2)
# 401 without header:
curl -is http://127.0.0.1:8789/admin/cache_stats | head -2
# 200 with header:
curl -is -H "x-admin-key: $AK" http://127.0.0.1:8789/admin/cache_stats | head -2
```

**Admin key management**
```bash
# Add key
curl -s -H "x-admin-key: $AK" "http://127.0.0.1:8789/admin/keys/add?key=newkey123" | jq .

# Check key
curl -s -H "x-admin-key: $AK" "http://127.0.0.1:8789/admin/keys/check?key=newkey123" | jq .

# Delete key
curl -s -H "x-admin-key: $AK" "http://127.0.0.1:8789/admin/keys/del?key=newkey123" | jq .

# (Optional) POST JSON supported if enabled:
# curl -X POST -H "x-admin-key: $AK" -d '{"key":"newkey123"}' http://127.0.0.1:8789/admin/keys/add
```

**Free translation**
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

**Bypass edge cache (backend TTL)**
```bash
curl -is -X POST "http://127.0.0.1:8789/translate?cache=no" \
  -H 'Content-Type: application/json' \
  -d '{"text":"Bazar korbo"}' | grep X-Backend-Cache
```

**Pro translation** (mint key → call; 200 from DB or 404 if not found unless fallback ON)
```bash
KEY="dev_$(openssl rand -hex 6)"
curl -s -H "x-admin-key: $AK" "http://127.0.0.1:8789/admin/keys/add?key=$KEY" | jq .

curl -is -X POST http://127.0.0.1:8789/translate/pro \
  -H 'Content-Type: application/json' -H "x-api-key: $KEY" \
  -d '{"text":"jam e pore asi","src_lang":"bn-rom","tgt_lang":"en"}' | head -6
```

---

## 🧬 Data & Schema

- **Import pipeline:** `normalize_jsonl.py` → `import_clean_jsonl.py`. No manual DB edits.
- **Identity:** Unique index on *(src_lang, roman_bn_norm, tgt_lang, pack)*; numbering is decorative.
- **Free vs Pro:** `safety_level` ≤ 1 = free; ≥ 2 = pro.
- **Release:** Export free client cache via `backend/scripts/export_client_cache.py`.

---

## 🔀 Branch & PR Expectations

- Branch names: `feat/*`, `fix/*`, `docs/*`, `ops/*`.
- Commit signing: Use SSH/GPG (required on protected branches).
- PR checklist:
  - No secrets in diff (`EDGE_SHIELD_TOKEN`, `ADMIN_KEY`, `whsec_`).
  - Update README / SECURITY / ARCH if behavior changes.
  - Dev smoke tests: free GET+POST, pro with `x-api-key`, admin 401→200.
  - CI/lint passes (if configured).

---

## 🚀 Production Cutover (Checklist)

```bash
# Set prod origin in wrangler.toml ([env.production]) to https://backend.dhkalign.com
cd infra/edge
wrangler secret put ADMIN_KEY --env production
wrangler secret put EDGE_SHIELD_TOKEN --env production
wrangler secret put STRIPE_WEBHOOK_SECRET --env production
wrangler deploy --env production
```

- Stripe: Use Interactive webhook builder for `checkout.session.completed` events (no signature failures in logs).
- Set Fly backend secrets (optional fallback): `OPENAI_API_KEY`, `ENABLE_GPT_FALLBACK`, `GPT_MODEL`, `GPT_MAX_TOKENS`, `GPT_TIMEOUT_MS`; then deploy Fly app.

---

## 🛠 Troubleshooting Cheatsheet

| Symptom                               | Cause                          | Fix                                                      |
|-------------------------------------|-------------------------------|----------------------------------------------------------|
| Origin 403 in logs (Worker→origin)  | Missing/invalid `x-edge-shield` | Set correct `EDGE_SHIELD_TOKEN`; enable enforcement       |
| Pro 404 on miss (fallback expected) | Fallback disabled or missing `OPENAI_API_KEY` | Set `OPENAI_API_KEY` & `ENABLE_GPT_FALLBACK` on Fly; redeploy |
| Admin API 401                       | Missing/invalid `x-admin-key`  | Provide correct admin key                                 |
| 429 quota                          | Per-key quota exceeded         | Wait for reset or reduce request rate                    |
| Cache always MISS                  | Method/path/body differ        | Send identical requests; avoid `?cache=no` for cache HIT |
| Stripe 400 signature               | Wrong `whsec_*` or mode mismatch | Set correct `STRIPE_WEBHOOK_SECRET`; verify mode         |

---

## 📄 Licenses & Contact

- **Code:** MIT (`LICENSE_CODE.md`)  
- **Data:** Proprietary (`LICENSE_DATA.md`)

Contact: **admin@dhkalign.com**