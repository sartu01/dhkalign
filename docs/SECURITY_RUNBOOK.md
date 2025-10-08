# DHK Align — Security Runbook (On‑Call)

Last updated: 2025‑09‑22

This is the **operational** runbook for on‑call. It assumes the code and docs are up to date (see `docs/SECURITY.md`, `docs/ARCHITECTURE.md`, `README.md`). Use this to triage, fix, and verify incidents quickly.

---

## 0) Golden invariants (do not drift)
- **Edge‑only ingress.** Clients call the **Cloudflare Worker**; only the Worker calls the private origin with the **internal** header `x‑edge‑shield`. Clients never send this header.
- **Secrets.** Dev secrets: `infra/edge/.dev.vars`. Prod secrets: Wrangler secrets. No secrets in git.
- **Admin guard.** All `/admin/*` endpoints require `x‑admin-key`.
- **Free route.** `/translate` supports **POST `{"text":"…"}`** (canonical) **and** **GET `?q=`**.
- **Pro route.** `/translate/pro` at the **Edge** requires `x‑api-key`; origin trusts only the shield.
- **Pro fallback (optional).** DB‑first → GPT fallback (if enabled) → auto‑insert into DB → serve.
- **Quotas & RL.** Edge daily per‑key quota (KV). Origin SlowAPI 60/min **only when enabled**.
- **Caching.** Edge KV → `CF‑Cache‑Edge: HIT|MISS`; origin TTL → `X‑Backend‑Cache: HIT|MISS` (bypass with `?cache=no`).
- **Stripe.** Verify `stripe‑signature` with 5‑minute tolerance; accept only `checkout.session.completed`; KV replay lock.
- **DB identity.** Uniqueness on *(src_lang, roman_bn_norm, tgt_lang, pack)*. `id` is cosmetic. Runtime DB = `backend/data/translations.db`.

---

## 1) Fast health checks
Run from any shell (prod Worker), and dev if relevant.

```bash
# Worker prod health (expect 200)
curl -is https://<WORKER_HOST>/edge/health | sed -n '1,2p'

# Origin health through Cloudflare → Fly (expect 200)
curl -is https://backend.dhkalign.com/health | sed -n '1,2p'
```

Dev (two tabs):
```bash
# Edge dev
dcd=~/Dev/dhkalign; cd $dcd/infra/edge; BROWSER=false wrangler dev --local --ip 127.0.0.1 --port 8789 --config wrangler.toml
# Backend dev (app_sqlite on 8090)
cd ~/Dev/dhkalign; source backend/.venv/bin/activate; \
EDGE_SHIELD_TOKEN=$(grep -m1 '^EDGE_SHIELD_TOKEN=' infra/edge/.dev.vars | cut -d= -f2) \
python -m uvicorn backend.app_sqlite:app --host 127.0.0.1 --port 8090 --reload
```

---

## 2) Common incidents → Runbooks

### A) Worker free route 530 (Upstream connection error)
**Symptom:** `HTTP 530` from Worker; origin health may fail.

**Cause:** Cloudflare named tunnel not running or mis‑ingress.

**Fix:**
```bash
# On backend host (where FastAPI runs)
# 1) make sure origin is alive locally
curl -is http://127.0.0.1:8090/health | sed -n '1,2p'

# 2) run tunnel (named)
cloudflared tunnel list  # note the tunnel name/uuid
cloudflared tunnel run dhkalign-origin
# if QUIC flaky: cloudflared tunnel run --protocol http2 dhkalign-origin

# 3) confirm public origin
curl -is https://backend.dhkalign.com/health | sed -n '1,2p'
```
**Persistent:** install LaunchAgent/Service to auto‑run the tunnel on boot.

---

### B) Origin returns 403 in logs (Worker→origin)
**Symptom:** Worker tail shows 403/401 from origin.

**Cause:** `x‑edge‑shield` mismatch (Worker secret vs backend env) or enforcement disabled.

**Fix:**
```bash
# set matching secrets in prod Worker
dcd=~/Dev/dhkalign/infra/edge; cd $dcd
wrangler secret put EDGE_SHIELD_TOKEN --env production  # paste the same value used by backend
wrangler deploy --env production
```
Restart backend with the same `EDGE_SHIELD_TOKEN`.

**Verify:**
```bash
curl -is https://<WORKER_HOST>/translate?q=ping | sed -n '1,2p'
```

---

### C) Stripe webhook signature fails (400)
**Symptom:** Worker tail shows `signature verification failed` on `/webhook/stripe`.

**Cause:** Wrong `whsec_…` in Worker, or Test/Live mismatch.

**Fix:**
```bash
cd ~/Dev/dhkalign/infra/edge
wrangler secret put STRIPE_WEBHOOK_SECRET --env production   # paste the endpoint's whsec_… from Stripe
yes | wrangler deploy --env production
```
Then, in Stripe **Interactive webhook endpoint builder** → send `checkout.session.completed`. Tail logs:
```bash
wrangler tail --env production
```

---

### D) Admin endpoint not locked (200 without header)
**Symptom:** `/admin/cache_stats` returns 200 with no `x-admin-key`.

**Fix:** Ensure global admin guard in Worker:
```js
function requireAdmin(request, env) {
  const got = request.headers.get('x-admin-key') || '';
  if (!env.ADMIN_KEY || got !== env.ADMIN_KEY) {
    return json({ error: 'unauthorized' }, 401);
  }
  return null;
}
// inside fetch():
if (url.pathname.startsWith('/admin/')) {
  const guard = requireAdmin(request, env);
  if (guard) return guard;
}
```
Restart dev Worker or deploy prod.

**Verify:** 401 without header; 200 with `x-admin-key`.

---

### E) Pro 401 at Edge (with a key)
**Symptom:** `/translate/pro` returns 401 with `x-api-key`.

**Cause:** Key not in KV (`apikey:<key>` ≠ "1").

**Fix:** Mint a dev key or use billing key handoff.
```bash
AK=$(grep -m1 '^ADMIN_KEY=' infra/edge/.dev.vars | cut -d= -f2)
KEY="dev_$(openssl rand -hex 6)"
curl -s -H "x-admin-key: $AK" "http://127.0.0.1:8789/admin/keys/add?key=$KEY" | jq .
```

---

### F) Free route confusion (405 vs 404)
- **405** on GET: enable GET in Worker or use POST `{ text }`.
- **404** on POST: exact‑match miss; use an actual free phrase from DB:
```bash
sqlite3 backend/data/translations.db \
 "SELECT banglish FROM translations WHERE COALESCE(safety_level,1)<=1 AND COALESCE(banglish,'')<>'' LIMIT 1;"
```
Then:
```bash
PHRASE='...'
curl -sX POST https://<WORKER_HOST>/translate -H 'content-type: application/json' \
  -d "{\"text\":\"$PHRASE\"}" | jq
```

### G) Pro returns 404 on a miss (fallback expected)
**Symptom:** 

`/translate/pro` returns 404 for a phrase not in DB, but fallback should have filled it.

**Causes:**
- `ENABLE_GPT_FALLBACK` is off, or `OPENAI_API_KEY` missing/invalid on Fly.
- OpenAI call timed out / 429 / 5xx (our handler masks unexpected errors as 404).

**Fix:**
```bash
# 1) Verify flags inside Fly (values are hidden)
flyctl ssh console -a dhkalign-backend -C \
"python -c \"import os;print('ENABLE=',os.getenv('ENABLE_GPT_FALLBACK'));print('HAS_KEY=',bool(os.getenv('OPENAI_API_KEY')));print('MODEL=',os.getenv('GPT_MODEL'))\""

# 2) (If needed) set secrets and redeploy
flyctl secrets set -a dhkalign-backend \
  OPENAI_API_KEY='sk-…' \
  ENABLE_GPT_FALLBACK='1' \
  GPT_MODEL='gpt-4o-mini' \
  GPT_MAX_TOKENS='128' \
  GPT_TIMEOUT_MS='2000'
cd ~/Dev/dhkalign && flyctl deploy -a dhkalign-backend

# 3) (Optional) enable lightweight debug for one run
flyctl secrets set -a dhkalign-backend DEBUG_FALLBACK='1'
cd ~/Dev/dhkalign && flyctl deploy -a dhkalign-backend
flyctl logs -a dhkalign-backend &  # then trigger one miss via Worker
```
**Verify:** First miss returns `{ ok:true, …, "source":"gpt" }`; repeating the same text returns `{ …, "source":"db" }`.

---

### G) Pro returns 404 on a miss (fallback expected)
**Symptom:** `/translate/pro` returns 404 for a phrase not in DB, but fallback should have filled it.

**Causes:**
- `ENABLE_GPT_FALLBACK` is off, or `OPENAI_API_KEY` missing/invalid on Fly.
- OpenAI call timed out / 429 / 5xx (our handler masks unexpected errors as 404).

**Fix:**
```bash
# 1) Verify flags inside Fly (values are hidden)
flyctl ssh console -a dhkalign-backend -C \
"python -c \"import os;print('ENABLE=',os.getenv('ENABLE_GPT_FALLBACK'));print('HAS_KEY=',bool(os.getenv('OPENAI_API_KEY')));print('MODEL=',os.getenv('GPT_MODEL'))\""

# 2) (If needed) set secrets and redeploy
flyctl secrets set -a dhkalign-backend \
  OPENAI_API_KEY='sk-…' \
  ENABLE_GPT_FALLBACK='1' \
  GPT_MODEL='gpt-4o-mini' \
  GPT_MAX_TOKENS='128' \
  GPT_TIMEOUT_MS='2000'
cd ~/Dev/dhkalign && flyctl deploy -a dhkalign-backend

# 3) (Optional) enable lightweight debug for one run
flyctl secrets set -a dhkalign-backend DEBUG_FALLBACK='1'
cd ~/Dev/dhkalign && flyctl deploy -a dhkalign-backend
flyctl logs -a dhkalign-backend &  # then trigger one miss via Worker
```
**Verify:** First miss returns `{ ok:true, …, "source":"gpt" }`; repeating the same text returns `{ …, "source":"db" }`.

---

## 3) On‑call smoke (dev)
```bash
# health
curl -s http://127.0.0.1:8789/edge/health | jq .
curl -s http://127.0.0.1:8090/health | jq .

# admin guard
AK=$(grep -m1 '^ADMIN_KEY=' infra/edge/.dev.vars | cut -d= -f2)
curl -is http://127.0.0.1:8789/admin/cache_stats | sed -n '1,2p'   # expect 401
curl -is -H "x-admin-key: $AK" http://127.0.0.1:8789/admin/cache_stats | sed -n '1,2p'   # expect 200

# free (both methods)
curl -sX POST http://127.0.0.1:8789/translate -H 'content-type: application/json' -d '{"text":"Bazar korbo"}' | jq
curl -s 'http://127.0.0.1:8789/translate?q=Bazar%20korbo' | jq

# pro (mint key → call)
KEY="dev_$(openssl rand -hex 6)"
curl -s -H "x-admin-key: $AK" "http://127.0.0.1:8789/admin/keys/add?key=$KEY" | jq .
curl -is -X POST http://127.0.0.1:8789/translate/pro -H 'content-type: application/json' -H "x-api-key: $KEY" -d '{"text":"jam e pore asi"}' | sed -n '1,4p'
```

---

## 4) Prod smoke
```bash
# Worker & origin
curl -is https://<WORKER_HOST>/edge/health | sed -n '1,2p'
curl -is https://backend.dhkalign.com/health | sed -n '1,2p'

# free (both)
curl -is -X POST https://<WORKER_HOST>/translate -H 'content-type: application/json' -d '{"text":"Bazar korbo"}' | sed -n '1,2p'
curl -is 'https://<WORKER_HOST>/translate?q=Bazar%20korbo' | sed -n '1,2p'

# stripe bad sig → 400
curl -is -X POST https://<WORKER_HOST>/webhook/stripe -H 'stripe-signature: test' -d '{}' | sed -n '1,3p'
```

---

## 5) Secrets & rotations
- **Prod (Wrangler):**
```bash
cd ~/Dev/dhkalign/infra/edge
wrangler secret put ADMIN_KEY --env production
wrangler secret put EDGE_SHIELD_TOKEN --env production
wrangler secret put STRIPE_WEBHOOK_SECRET --env production
wrangler deploy --env production
```
- **Backend (Fly) — GPT fallback (optional):** set `OPENAI_API_KEY`, `ENABLE_GPT_FALLBACK=1`, `GPT_MODEL`, `GPT_MAX_TOKENS`, `GPT_TIMEOUT_MS`, then `flyctl deploy -a dhkalign-backend`.
- **Stripe “Roll secret”:** If you rotate signing secret in Stripe, immediately set the new `whsec_…` as `STRIPE_WEBHOOK_SECRET` and deploy, or your webhook will 400.
- **Dev:** `.dev.vars` → `ADMIN_KEY=…`, `EDGE_SHIELD_TOKEN=…`, `STRIPE_WEBHOOK_SECRET=whsec_…`.
- **Backend (Fly) — GPT fallback (optional):** set 
`OPENAI_API_KEY`, `ENABLE_GPT_FALLBACK=1`, `GPT_MODEL`, `GPT_MAX_TOKENS`, `GPT_TIMEOUT_MS`, then `flyctl deploy -a dhkalign-backend`.

---

## 6) KV operations (quick)
```bash
# admin key ops
AK=$(grep -m1 '^ADMIN_KEY=' infra/edge/.dev.vars | cut -d= -f2)
curl -s -H "x-admin-key: $AK" "http://127.0.0.1:8789/admin/keys/add?key=demo_123" | jq .
curl -s -H "x-admin-key: $AK" "http://127.0.0.1:8789/admin/keys/check?key=demo_123" | jq .
curl -s -H "x-admin-key: $AK" "http://127.0.0.1:8789/admin/keys/del?key=demo_123" | jq .

# session → key (simulate Stripe)
SID="sid_test_$(openssl rand -hex 6)"
( cd infra/edge && wrangler kv:key put --namespace USAGE "session_to_key:$SID" "demo_123" --local )
```

---

## 7) Logging & monitoring
- **Worker prod logs:** `wrangler tail --env production`
- **Origin logs:** Uvicorn/ASGI logs (enable structured logs; avoid full text).
- **Tunnel logs:** `/tmp/cloudflared.err` (if using LaunchAgent), or foreground output.
- **Metrics:** (recommended) add `/metrics` Prometheus endpoint on origin (req count, latencies, 4xx/5xx, cache hit rate).

---

## 8) Post‑incident checklist
- [ ] Document root cause and the exact fix in `docs/SECURITY_RUN_LOG.md` (or issue).
- [ ] Verify Worker & origin health, admin guard 401→200, free GET+POST 200, pro auth 200/404 JSON.
- [ ] If secrets rotated: confirm new secrets are stored in password manager.
- [ ] If tunnel changed: ensure persistence (LaunchAgent/Service) so it restarts on boot.

---

## References
- Architecture: `docs/ARCHITECTURE.md`
- Security model: `docs/SECURITY.md`
- Privacy: `docs/PRIVACY.md`
- Execution Deliverables: `docs/EXECUTION_DELIVERABLES.md`
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