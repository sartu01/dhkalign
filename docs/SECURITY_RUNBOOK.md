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

# Origin health through tunnel (expect 200)
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
- **Stripe “Roll secret”:** If you rotate signing secret in Stripe, immediately set the new `whsec_…` as `STRIPE_WEBHOOK_SECRET` and deploy, or your webhook will 400.
- **Dev:** `.dev.vars` → `ADMIN_KEY=…`, `EDGE_SHIELD_TOKEN=…`, `STRIPE_WEBHOOK_SECRET=whsec_…`.

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