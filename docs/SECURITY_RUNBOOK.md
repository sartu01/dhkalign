# DHK Align — Security Runbook (On‑Call)

Last updated: 2025‑10‑07

**Purpose:** fast, copy‑paste fixes for live incidents. Mirrors `docs/SECURITY.md` / `docs/ARCHITECTURE.md`.

---
## 0) Golden invariants (do not drift)
- **Edge‑only ingress.** Clients call the **Cloudflare Worker**; only the Worker calls origin with **internal** `x-edge-shield`. Clients never send it.
- **Admin guard.** All `/admin/*` require `x-admin-key`.
- **Free route.** At **Edge** use **GET `/api/translate?q=…`** (canonical) and **POST `/translate`** with JSON `{ "q": "…" }`.
- **Pro route.** `/translate/pro` requires `x-api-key` at Edge; origin trusts only shield.
- **Fallback (optional).** DB‑first → GPT‑4o‑mini → auto‑insert → serve.
- **Quotas & RL.** Edge daily per‑key quota (KV). Origin SlowAPI 60/min **when enabled**.
- **Caching.** Edge KV → `CF-Cache-Edge: HIT|MISS`; origin TTL → `X-Backend-Cache: HIT|MISS` (`?cache=no` bypass).
- **Stripe.** Verify `stripe-signature` (5‑min tolerance); accept only `checkout.session.completed`; KV replay lock.
- **DB identity.** Unique `(src_lang, roman_bn_norm, tgt_lang, pack)`; `id` cosmetic. Runtime DB: `backend/data/translations.db`.

---
## 1) One‑liners (health)
```bash
# Worker prod
curl -is https://edge.dhkalign.com/edge/health | sed -n '1,2p'
# Origin (Fly via CF)
curl -is https://backend.dhkalign.com/health | sed -n '1,2p'
# Metrics
curl -is https://backend.dhkalign.com/metrics | sed -n '1,3p'
```

Dev (two tabs):
```bash
# Edge
cd ~/Dev/dhkalign/infra/edge; BROWSER=false wrangler dev --local --ip 127.0.0.1 --port 8789 --config wrangler.toml
# Backend
cd ~/Dev/dhkalign; source backend/.venv/bin/activate; \
EDGE_SHIELD_TOKEN=$(grep -m1 '^EDGE_SHIELD_TOKEN=' infra/edge/.dev.vars | cut -d= -f2) \
python -m uvicorn backend.app_sqlite:app --host 127.0.0.1 --port 8090 --reload
```

---
## 2) Incidents → Fix recipes

### A) Worker 530 / upstream error
**Cause:** CF → origin path broken (DNS/tunnel/host).
```bash
curl -is https://backend.dhkalign.com/health | sed -n '1,2p'   # expect 200
# If 5xx: redeploy Fly or restart machine
flyctl status -a dhkalign-backend; flyctl logs -a dhkalign-backend -n 100
```

### B) Origin 403/401 (shield)
**Cause:** Missing/mismatched `x-edge-shield`.
```bash
# Set same shield in Worker + redeploy
cd ~/Dev/dhkalign/infra/edge
printf '%s' "$(openssl rand -hex 16)" | wrangler secret put EDGE_SHIELD_TOKEN --env production
wrangler deploy --env production
```
Confirm backend uses identical token; redeploy Fly if you changed it.

### C) Admin not locked
**Symptom:** `/admin/cache_stats` 200 without header.
**Fix:** enforce guard in Worker.
```js
function requireAdmin(req, env){ const k=req.headers.get('x-admin-key')||''; if(!env.ADMIN_KEY||k!==env.ADMIN_KEY) return json({error:'unauthorized'},401); return null }
// in fetch(): if (url.pathname.startsWith('/admin/')) { const g=requireAdmin(request, env); if (g) return g }
```
Redeploy; verify 401→200 with header.

### D) Pro 401 at Edge (invalid api key)
**Cause:** KV lacks `apikey:<key>`.
```bash
# Mint key (dev)
AK=$(grep -m1 '^ADMIN_KEY=' infra/edge/.dev.vars | cut -d= -f2)
KEY="dev_$(openssl rand -hex 6)"
curl -s -H "x-admin-key: $AK" "http://127.0.0.1:8789/admin/keys/add?key=$KEY"
```
Prod: reset ADMIN and mint (script): `scripts/reset_admin_and_mint_prod_key.sh`.

### E) Stripe webhook 400 (signature fail)
**Fix:** set correct `STRIPE_WEBHOOK_SECRET` (the endpoint’s `whsec_…`), 5‑min tolerance enforced.
```bash
cd ~/Dev/dhkalign/infra/edge
wrangler secret put STRIPE_WEBHOOK_SECRET --env production
wrangler deploy --env production
wrangler tail --env production   # send test event from Stripe builder
```

### F) Pro 404 on miss (fallback expected)
**Causes:** fallback disabled; missing/invalid `OPENAI_API_KEY`; model 429/timeout.
```bash
# Inspect flags on Fly (prints booleans/names, not secrets)
flyctl ssh console -a dhkalign-backend -C \
"python -c \"import os;print('ENABLE=',os.getenv('ENABLE_GPT_FALLBACK'));print('HAS_KEY=',bool(os.getenv('OPENAI_API_KEY')));print('MODEL=',os.getenv('GPT_MODEL'))\""
# Enable fallback
flyctl secrets set -a dhkalign-backend OPENAI_API_KEY='sk-…' ENABLE_GPT_FALLBACK='1' GPT_MODEL='gpt-4o-mini' GPT_MAX_TOKENS='128' GPT_TIMEOUT_MS='2000'
cd ~/Dev/dhkalign && flyctl deploy -a dhkalign-backend
```
(Optional for one run) `DEBUG_FALLBACK=1` as Fly secret, redeploy, tail logs.

### G) Free 405 vs 404
- **405 on GET** → use **`GET /api/translate?q=…`** (Edge) or enable GET in Worker.
- **404 on POST** → use a real free phrase from DB and **JSON `{ "q": "…" }`**.
```bash
sqlite3 backend/data/translations.db "SELECT banglish FROM translations WHERE COALESCE(safety_level,1)<=1 AND COALESCE(banglish,'')<>'' LIMIT 1;"
```
```bash
curl -sX POST https://edge.dhkalign.com/translate -H 'content-type: application/json' \
  -d '{"q":"'"$PHRASE"'"}' | jq
```

---
## 3) On‑call smoke (dev)
```bash
# Health
curl -s http://127.0.0.1:8789/edge/health | jq .
curl -s http://127.0.0.1:8090/health | jq .
# Admin guard
AK=$(grep -m1 '^ADMIN_KEY=' infra/edge/.dev.vars | cut -d= -f2)
curl -is http://127.0.0.1:8789/admin/cache_stats | sed -n '1,2p'   # 401
curl -is -H "x-admin-key: $AK" http://127.0.0.1:8789/admin/cache_stats | sed -n '1,2p'   # 200
# Free
curl -sX POST http://127.0.0.1:8789/translate -H 'content-type: application/json' -d '{"q":"Bazar korbo"}' | jq
curl -s    http://127.0.0.1:8789/api/translate?q=Bazar%20korbo | jq
# Pro
KEY="dev_$(openssl rand -hex 6)"
curl -s -H "x-admin-key: $AK" "http://127.0.0.1:8789/admin/keys/add?key=$KEY" | jq .
curl -is -X POST http://127.0.0.1:8789/translate/pro -H 'content-type: application/json' -H "x-api-key: $KEY" -d '{"q":"jam e pore asi"}' | sed -n '1,4p'
```

---
## 4) Prod smoke (fast)
```bash
curl -is https://edge.dhkalign.com/edge/health | sed -n '1,2p'
curl -is https://backend.dhkalign.com/health | sed -n '1,2p'
# Free
curl -is -X POST https://edge.dhkalign.com/translate -H 'content-type: application/json' -d '{"q":"Bazar korbo"}' | sed -n '1,2p'
curl -is 'https://edge.dhkalign.com/api/translate?q=Bazar%20korbo' | sed -n '1,2p'
# Stripe bad sig → 400
curl -is -X POST https://edge.dhkalign.com/webhook/stripe -H 'stripe-signature: test' -d '{}' | sed -n '1,3p'
```

---
## 5) Secrets & rotations
- **Worker (prod):**
```bash
cd ~/Dev/dhkalign/infra/edge
wrangler secret put ADMIN_KEY --env production
wrangler secret put EDGE_SHIELD_TOKEN --env production
wrangler secret put STRIPE_WEBHOOK_SECRET --env production
wrangler deploy --env production
```
- **Backend (Fly):** set `OPENAI_API_KEY`, `ENABLE_GPT_FALLBACK`, `GPT_MODEL`, `GPT_MAX_TOKENS`, `GPT_TIMEOUT_MS`, then `flyctl deploy -a dhkalign-backend`.
- **Scripts:** `scripts/reset_admin_and_mint_prod_key.sh` (resets ADMIN_KEY → deploys → mints API key to KV, saves to `~/.dhkalign_secrets`).

---
## 6) KV & admin ops (quick)
```bash
AK=$(grep -m1 '^ADMIN_KEY=' infra/edge/.dev.vars | cut -d= -f2)
# add/check/del
curl -s -H "x-admin-key: $AK" "http://127.0.0.1:8789/admin/keys/add?key=demo_123" | jq .
curl -s -H "x-admin-key: $AK" "http://127.0.0.1:8789/admin/keys/check?key=demo_123" | jq .
curl -s -H "x-admin-key: $AK" "http://127.0.0.1:8789/admin/keys/del?key=demo_123" | jq .
```

---
## 7) Monitoring & post‑incident
- **Worker logs:** `wrangler tail --env production`
- **Origin logs:** `flyctl logs -a dhkalign-backend -n 100`
- **Metrics:** `/metrics` Prometheus counters (db hit, fallback, fail, latency).
- **After fix:** document RCA; verify health; confirm admin guard 401→200; free GET/POST 200; pro 200/404 JSON; rotate compromised secrets.
# DHK Align — Security Runbook (On‑Call)

Last updated: 2025‑10‑07

**Purpose:** fast, copy‑paste fixes for live incidents. Mirrors `docs/SECURITY.md` / `docs/ARCHITECTURE.md`.

---
## 0) Golden invariants (do not drift)
- **Edge‑only ingress.** Clients call the **Cloudflare Worker**; only the Worker calls origin with **internal** `x-edge-shield`. Clients never send it.
- **Admin guard.** All `/admin/*` require `x-admin-key`.
- **Free route.** `/translate` supports POST `{text}` (canonical) and GET `?q=`.
- **Pro route.** `/translate/pro` requires `x-api-key` at Edge; origin trusts only shield.
- **Fallback (optional).** DB‑first → GPT‑4o‑mini → auto‑insert → serve.
- **Quotas & RL.** Edge daily per‑key quota (KV). Origin SlowAPI 60/min **when enabled**.
- **Caching.** Edge KV → `CF‑Cache‑Edge: HIT|MISS`; origin TTL → `X‑Backend‑Cache: HIT|MISS` (`?cache=no` bypass).
- **Stripe.** Verify `stripe-signature` (5‑min tolerance); accept only `checkout.session.completed`; KV replay lock.
- **DB identity.** Unique `(src_lang, roman_bn_norm, tgt_lang, pack)`; `id` cosmetic. Runtime DB: `backend/data/translations.db`.

---
## 1) One‑liners (health)
```bash
# Worker prod
curl -is https://<WORKER_HOST>/edge/health | sed -n '1,2p'
# Origin (Fly via CF)
curl -is https://backend.dhkalign.com/health | sed -n '1,2p'
# Metrics
curl -is https://backend.dhkalign.com/metrics | sed -n '1,3p'
```

Dev (two tabs):
```bash
# Edge
cd ~/Dev/dhkalign/infra/edge; BROWSER=false wrangler dev --local --ip 127.0.0.1 --port 8789 --config wrangler.toml
# Backend
cd ~/Dev/dhkalign; source backend/.venv/bin/activate; \
EDGE_SHIELD_TOKEN=$(grep -m1 '^EDGE_SHIELD_TOKEN=' infra/edge/.dev.vars | cut -d= -f2) \
python -m uvicorn backend.app_sqlite:app --host 127.0.0.1 --port 8090 --reload
```

---
## 2) Incidents → Fix recipes

### A) Worker 530 / upstream error
**Cause:** CF → origin path broken (DNS/tunnel/host).
```bash
curl -is https://backend.dhkalign.com/health | sed -n '1,2p'   # expect 200
# If 5xx: redeploy Fly or restart machine
flyctl status -a dhkalign-backend; flyctl logs -a dhkalign-backend -n 100
```

### B) Origin 403/401 (shield)
**Cause:** Missing/mismatched `x-edge-shield`.
```bash
# Set same shield in Worker + redeploy
cd ~/Dev/dhkalign/infra/edge
printf '%s' "$(openssl rand -hex 16)" | wrangler secret put EDGE_SHIELD_TOKEN --env production
wrangler deploy --env production
```
Confirm backend uses identical token; redeploy Fly if you changed it.

### C) Admin not locked
**Symptom:** `/admin/cache_stats` 200 without header.
**Fix:** enforce guard in Worker.
```js
function requireAdmin(req, env){ const k=req.headers.get('x-admin-key')||''; if(!env.ADMIN_KEY||k!==env.ADMIN_KEY) return json({error:'unauthorized'},401); return null }
// in fetch(): if (url.pathname.startsWith('/admin/')) { const g=requireAdmin(request, env); if (g) return g }
```
Redeploy; verify 401→200 with header.

### D) Pro 401 at Edge (invalid api key)
**Cause:** KV lacks `apikey:<key>`.
```bash
# Mint key (dev)
AK=$(grep -m1 '^ADMIN_KEY=' infra/edge/.dev.vars | cut -d= -f2)
KEY="dev_$(openssl rand -hex 6)"
curl -s -H "x-admin-key: $AK" "http://127.0.0.1:8789/admin/keys/add?key=$KEY"
```
Prod: reset ADMIN and mint (script): `scripts/reset_admin_and_mint_prod_key.sh`.

### E) Stripe webhook 400 (signature fail)
**Fix:** set correct `STRIPE_WEBHOOK_SECRET` (the endpoint’s `whsec_…`), 5‑min tolerance enforced.
```bash
cd ~/Dev/dhkalign/infra/edge
wrangler secret put STRIPE_WEBHOOK_SECRET --env production
wrangler deploy --env production
wrangler tail --env production   # send test event from Stripe builder
```

### F) Pro 404 on miss (fallback expected)
**Causes:** fallback disabled; missing/invalid `OPENAI_API_KEY`; model 429/timeout.
```bash
# Inspect flags on Fly (prints booleans/names, not secrets)
flyctl ssh console -a dhkalign-backend -C \
"python -c \"import os;print('ENABLE=',os.getenv('ENABLE_GPT_FALLBACK'));print('HAS_KEY=',bool(os.getenv('OPENAI_API_KEY')));print('MODEL=',os.getenv('GPT_MODEL'))\""
# Enable fallback
flyctl secrets set -a dhkalign-backend OPENAI_API_KEY='sk-…' ENABLE_GPT_FALLBACK='1' GPT_MODEL='gpt-4o-mini' GPT_MAX_TOKENS='128' GPT_TIMEOUT_MS='2000'
cd ~/Dev/dhkalign && flyctl deploy -a dhkalign-backend
```
(Optional for one run) `DEBUG_FALLBACK=1` as Fly secret, redeploy, tail logs.

### G) Free 405 vs 404
- 405 on GET → enable GET in Worker or use POST.
- 404 on POST → use real free phrase from DB.
```bash
sqlite3 backend/data/translations.db "SELECT banglish FROM translations WHERE COALESCE(safety_level,1)<=1 AND COALESCE(banglish,'')<>'' LIMIT 1;"
```

---
## 3) On‑call smoke (dev)
```bash
# Health
curl -s http://127.0.0.1:8789/edge/health | jq .
curl -s http://127.0.0.1:8090/health | jq .
# Admin guard
AK=$(grep -m1 '^ADMIN_KEY=' infra/edge/.dev.vars | cut -d= -f2)
curl -is http://127.0.0.1:8789/admin/cache_stats | sed -n '1,2p'   # 401
curl -is -H "x-admin-key: $AK" http://127.0.0.1:8789/admin/cache_stats | sed -n '1,2p'   # 200
# Free
curl -sX POST http://127.0.0.1:8789/translate -H 'content-type: application/json' -d '{"text":"Bazar korbo"}' | jq
curl -s    http://127.0.0.1:8789/translate?q=Bazar%20korbo | jq
# Pro
KEY="dev_$(openssl rand -hex 6)"
curl -s -H "x-admin-key: $AK" "http://127.0.0.1:8789/admin/keys/add?key=$KEY" | jq .
curl -is -X POST http://127.0.0.1:8789/translate/pro -H 'content-type: application/json' -H "x-api-key: $KEY" -d '{"text":"jam e pore asi"}' | sed -n '1,4p'
```

---
## 4) Prod smoke (fast)
```bash
curl -is https://<WORKER_HOST>/edge/health | sed -n '1,2p'
curl -is https://backend.dhkalign.com/health | sed -n '1,2p'
# Free
curl -is -X POST https://<WORKER_HOST>/translate -H 'content-type: application/json' -d '{"text":"Bazar korbo"}' | sed -n '1,2p'
# Stripe bad sig → 400
curl -is -X POST https://<WORKER_HOST>/webhook/stripe -H 'stripe-signature: test' -d '{}' | sed -n '1,3p'
```

---
## 5) Secrets & rotations
- **Worker (prod):**
```bash
cd ~/Dev/dhkalign/infra/edge
wrangler secret put ADMIN_KEY --env production
wrangler secret put EDGE_SHIELD_TOKEN --env production
wrangler secret put STRIPE_WEBHOOK_SECRET --env production
wrangler deploy --env production
```
- **Backend (Fly):** set `OPENAI_API_KEY`, `ENABLE_GPT_FALLBACK`, `GPT_MODEL`, `GPT_MAX_TOKENS`, `GPT_TIMEOUT_MS`, then `flyctl deploy -a dhkalign-backend`.
- **Scripts:** `scripts/reset_admin_and_mint_prod_key.sh` (resets ADMIN_KEY → deploys → mints API key to KV, saves to `~/.dhkalign_secrets`).

---
## 6) KV & admin ops (quick)
```bash
AK=$(grep -m1 '^ADMIN_KEY=' infra/edge/.dev.vars | cut -d= -f2)
# add/check/del
curl -s -H "x-admin-key: $AK" "http://127.0.0.1:8789/admin/keys/add?key=demo_123" | jq .
curl -s -H "x-admin-key: $AK" "http://127.0.0.1:8789/admin/keys/check?key=demo_123" | jq .
curl -s -H "x-admin-key: $AK" "http://127.0.0.1:8789/admin/keys/del?key=demo_123" | jq .
```

---
## 7) Monitoring & post‑incident
- **Worker logs:** `wrangler tail --env production`
- **Origin logs:** `flyctl logs -a dhkalign-backend -n 100`
- **Metrics:** `/metrics` Prometheus counters (db hit, fallback, fail, latency).
- **After fix:** document RCA; verify health; confirm admin guard 401→200; free GET/POST 200; pro 200/404 JSON; rotate compromised secrets.