# DHK Align — Contributing Guide

Thanks for helping build DHK Align. This guide tells you how to run the stack locally, how we keep the repo secure, how to contribute code/data safely, and the checks to run before you open a PR.

---

## 🔒 Ground rules (read first)
- **Edge‑only ingress.** Clients call the **Cloudflare Worker**; only the Worker calls the private origin with the **internal** header `x-edge-shield`. Clients never send this header.
- **Secrets.** Dev secrets live in `infra/edge/.dev.vars`. Prod secrets are Wrangler secrets. **Never** commit secrets to git.
- **Admin guard.** All `/admin/*` endpoints require `x-admin-key`.
- **JSON contract.** Responses are `{ ok:true, data:{...} }` or `{ ok:false, error:"..." }`. No HTML error pages.
- **One DB path.** Runtime DB = `backend/data/translations.db`.
- **Identity invariant.** De‑dup at DB level: *(src_lang, roman_bn_norm, tgt_lang, pack)* is unique. `id` is cosmetic.
- **Pro fallback (optional).** Origin can call a GPT model on DB miss (gpt‑4o‑mini by default) under tight limits; results are auto‑inserted for next time. Toggle via Fly secrets.

---

## ⚡ Quick Start (Dev, 2 Tabs)
**Prerequisites**: Python ≥ 3.11, Node ≥ 18, `jq`, `sqlite3`, `cloudflared`, `wrangler` 

**Server tab**
```bash
cd ~/Dev/dhkalign
# load dev shield token from Worker dev vars
export EDGE_SHIELD_TOKEN="$(grep -m1 '^EDGE_SHIELD_TOKEN=' infra/edge/.dev.vars | cut -d= -f2)" \
  EDGE_SHIELD_ENFORCE=1 BACKEND_CACHE_TTL=180
./scripts/run_server.sh   # backend at http://127.0.0.1:8090
```
(Alt) `./scripts/server_up.sh`

**Work tab (Edge)**
```bash
cd ~/Dev/dhkalign/infra/edge
BROWSER=false wrangler dev --local --ip 127.0.0.1 --port 8789 --config wrangler.toml
# dev Worker at http://127.0.0.1:8789
```

**Secrets**
- Dev secrets: `infra/edge/.dev.vars`  
- Prod secrets: Wrangler secrets

### Backend (Fly) Environment Variables
- `OPENAI_API_KEY` — OpenAI key (sk‑…), required only if fallback is enabled
- `ENABLE_GPT_FALLBACK` — set to `1` to enable GPT fallback on DB miss
- `GPT_MODEL` — model name (default: `gpt‑4o‑mini`)
- `GPT_MAX_TOKENS` — max tokens for fallback responses (default: `128`)
- `GPT_TIMEOUT_MS` — timeout in milliseconds (default: `2000`)

## 🤖 GPT Fallback (optional)

Enable GPT fallback in production so DB misses return a model translation and are auto‑inserted for next time:

```bash
flyctl secrets set -a dhkalign-backend \
  OPENAI_API_KEY='sk-…' \
  ENABLE_GPT_FALLBACK='1' \
  GPT_MODEL='gpt-4o-mini' \
  GPT_MAX_TOKENS='128' \
  GPT_TIMEOUT_MS='2000'
cd ~/Dev/dhkalign && flyctl deploy -a dhkalign-backend
```

First miss via `/translate/pro` will return `{ ok:true, data:{ …, "source":"gpt" } }`; repeated calls return `{ …, "source":"db" }` after auto‑insert.

---

## 🧪 Curl tests (copy/paste)

**Edge health**
```bash
curl -s http://127.0.0.1:8789/edge/health | jq .
```

**Admin cache stats (locked)**
```bash
AK=$(grep -m1 '^ADMIN_KEY=' infra/edge/.dev.vars | cut -d= -f2)
# 401 without header:
curl -is http://127.0.0.1:8789/admin/cache_stats | sed -n '1,2p'
# 200 with header:
curl -is -H "x-admin-key: $AK" http://127.0.0.1:8789/admin/cache_stats | sed -n '1,2p'
```

**Admin key management**
```bash
# Add key (GET with ?key=...)
curl -s -H "x-admin-key: $AK" \
  "http://127.0.0.1:8789/admin/keys/add?key=newkey123" | jq .

# Check key (GET with ?key=...)
curl -s -H "x-admin-key: $AK" \
  "http://127.0.0.1:8789/admin/keys/check?key=newkey123" | jq .

# Delete key (GET with ?key=...)
curl -s -H "x-admin-key: $AK" \
  "http://127.0.0.1:8789/admin/keys/del?key=newkey123" | jq .

# (Optional) POST JSON is supported if enabled in the Worker:
# curl -X POST -H "x-admin-key: $AK" -d '{"key":"newkey123"}' http://127.0.0.1:8789/admin/keys/add
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

**Pro** (mint key → call; 200 from DB or 404 if not found unless fallback is ON)

```bash
KEY="dev_$(openssl rand -hex 6)"
curl -s -H "x-admin-key: $AK" "http://127.0.0.1:8789/admin/keys/add?key=$KEY" | jq .

curl -is -X POST http://127.0.0.1:8789/translate/pro \
  -H 'Content-Type: application/json' -H "x-api-key: $KEY" \
  -d '{"text":"jam e pore asi","src_lang":"bn-rom","tgt_lang":"en"}' | sed -n '1,6p'
```

---

## 🧬 Data & schema (no surprises)
- **Import pipeline:** `normalize_jsonl.py` → `import_clean_jsonl.py`. No ad‑hoc DB edits.
- **Identity:** unique index on *(src_lang, roman_bn_norm, tgt_lang, pack)* — numbering is decorative.
- **Free vs Pro:** `safety_level` **≤1** = free, **≥2** = pro.
- **Release:** export free client cache via `backend/scripts/export_client_cache.py`.

---

## 🧰 Linting & security checks
- Python security scan:
```bash
bandit -r backend/
```
- (Optional) add pre‑commit hooks, ruff/black if desired.

---

## 🔀 Branch & PR expectations
- **Branch names:** `feat/*`, `fix/*`, `docs/*`, `ops/*`.
- **Commit signing:** use SSH/GPG signing (required on protected branches).
- **PR checklist:**
  - [ ] No secrets in diff (search for `EDGE_SHIELD_TOKEN`, `ADMIN_KEY`, `whsec_`)
  - [ ] README / SECURITY / ARCH updated if behavior changes
  - [ ] Dev smoke: free GET+POST, pro with x‑api‑key, admin 401→200
  - [ ] CI/lint passes (if configured)

---

## 🚀 Production cutover (checklist)
```bash
# set prod origin in wrangler.toml (default + [env.production]) to https://backend.dhkalign.com
cd infra/edge
wrangler secret put ADMIN_KEY --env production
wrangler secret put EDGE_SHIELD_TOKEN --env production
wrangler secret put STRIPE_WEBHOOK_SECRET --env production
wrangler deploy --env production
```
- Stripe → endpoint → **Interactive webhook builder** → send `checkout.session.completed` (no signature failures in tail).
- Set backend secrets on Fly (optional fallback): OPENAI_API_KEY, ENABLE_GPT_FALLBACK, GPT_MODEL, GPT_MAX_TOKENS, GPT_TIMEOUT_MS; then deploy Fly app.

---

## 🛠 Troubleshooting Cheatsheet
| Symptom                                   | Possible Cause                     | Fix                                                     |
|-------------------------------------------|------------------------------------|---------------------------------------------------------|
| Origin returns 403 in logs (Worker→origin) | Missing/invalid `x-edge-shield`    | Set correct EDGE_SHIELD_TOKEN; enable enforcement       |
| Pro returns 404 on a miss (fallback expected) | Fallback disabled or missing OPENAI_API_KEY | Set OPENAI_API_KEY & ENABLE_GPT_FALLBACK on Fly, redeploy; verify from Fly |
| Admin API 401                              | Missing/invalid `x-admin-key`      | Provide correct admin key                                |
| 429 quota                                  | Daily per‑key quota exceeded       | Wait for reset / reduce request rate                    |
| Cache always MISS                          | Method/path/body differ             | Send identical requests; avoid `?cache=no` for cache HIT|
| Stripe 400 signature                       | Wrong `whsec_*` or test/live mismatch | Set correct STRIPE_WEBHOOK_SECRET; verify mode        |

---

## 📄 Licenses & Contact
- **Code:** MIT (see `LICENSE_CODE.md`)  
- **Data:** Proprietary (see `LICENSE_DATA.md`)

Contact: **admin@dhkalign.com**