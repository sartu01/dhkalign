# DHK Align — Property Defense & Abuse Response

_Last updated: 2025‑09‑22_

This document outlines how DHK Align protects its code, data, and runtime property; detects abuse; and responds using defined runbooks. It complements `README.md`, `docs/SECURITY.md`, `docs/ARCHITECTURE.md`, `docs/PRIVACY.md`, and `docs/EXECUTION_DELIVERABLES.md`.

---

## 0) Golden Invariants

- **Edge-only ingress:** Clients call the Cloudflare Worker; only the Worker calls the private origin with header `x-edge-shield`. Clients never send this header.
- **Admin guard:** All `/admin/*` endpoints require `x-admin-key`.
- **Free route:** `/translate` supports POST `{"text":"…"}` and GET `?q=`.
- **Pro route:** `/translate/pro` at Edge requires `x-api-key`; origin trusts only requests with `x-edge-shield`.
- **Pro fallback (optional):** DB-first → GPT fallback (if enabled) → auto-insert → serve.
- **Quotas & rate limits:** Edge enforces daily per-key quota (KV); origin SlowAPI 60/min when enabled.
- **One-time key handoff:** `/billing/key?session_id=…` returns once; origin allowlisted.
- **No text storage by default:** Edge does not store translation text; origin logs avoid full text.
- **Identity invariant (DB):** Uniqueness on `(src_lang, roman_bn_norm, tgt_lang, pack)`; `id` is cosmetic. Runtime DB at `backend/data/translations.db`.
- **Licenses:** Code = MIT; Data = Proprietary (see `LICENSE_CODE.md`, `LICENSE_DATA.md`).

---

## 1) Property Surface & Protections

### Code
- No secrets in git; dev secrets in `infra/edge/.dev.vars`, prod secrets via Wrangler.
- Commit signing on protected branches.
- Security scanning: `bandit -r backend/` before PR merge.

### Data (Proprietary)
- Access only through Edge (Pro requires API key); no public dumps.
- Deduplication and provenance via invariant key; import pipeline `normalize_jsonl.py → import_clean_jsonl.py`.
- Optional watermarking (planned): embed low-impact canary pairs per pack for tracing leaks.

### Runtime (Edge + Origin)
- Gating: `x-api-key` on `/translate/pro`; `x-admin-key` on `/admin/*`.
- Shield: Worker adds `x-edge-shield`; origin rejects Pro requests without it.
- Quotas: KV daily per-key quota (e.g., 1000/day) → HTTP 429.
- CORS/CSP: allowlist origins; Stripe host allowed; explicit dev hosts (`127.0.0.1:5173`, `127.0.0.1:8789`).
- Caching: Edge KV (`CF-Cache-Edge: HIT|MISS`); origin TTL (`X-Backend-Cache: HIT|MISS`); bypass with `?cache=no`.
- Stripe: Signature check (5-min tolerance), event allowlist (`checkout.session.completed`), KV replay lock; keys stored as `apikey:<key> = "1"`, metadata at `apikey.meta:<key>`.
- Fallback controls (origin): If enabled, origin calls OpenAI (default `gpt-4o-mini`) with strict limits; first miss auto-inserts a pro row, subsequent calls hit DB. Toggle via Fly secrets.

### Backend Environment Variables
- `OPENAI_API_KEY` — OpenAI key (sk-…), required if fallback enabled
- `ENABLE_GPT_FALLBACK` — `1` to enable GPT fallback on DB miss
- `GPT_MODEL` — model name (default: `gpt-4o-mini`)
- `GPT_MAX_TOKENS` — max tokens for fallback (default: `128`)
- `GPT_TIMEOUT_MS` — timeout in ms (default: `2000`)

---

## 2) GPT Fallback (Optional)

Enable GPT fallback to serve DB misses with model translations, auto-inserting results:

```bash
flyctl secrets set -a dhkalign-backend \
  OPENAI_API_KEY='sk-…' \
  ENABLE_GPT_FALLBACK='1' \
  GPT_MODEL='gpt-4o-mini' \
  GPT_MAX_TOKENS='128' \
  GPT_TIMEOUT_MS='2000'
cd ~/Dev/dhkalign && flyctl deploy -a dhkalign-backend
```

First miss via `/translate/pro` returns `{ ok:true, data:{ …, "source":"gpt" } }`; repeated calls return `{ …, "source":"db" }`.

---

## 3) Abuse Taxonomy & Responses

### A) Key Sharing / Bulk Scraping
**Signal:** Traffic bursts from many IPs on one key; daily quota hits; unusual cache patterns.

**Actions:**
1. Throttle key quota; alert user.
2. Mint replacement key; disable old key (`USAGE.del apikey:<old>` or set flag to 0); update user.
3. If abuse continues, suspend key per policy.

**KV ops:**
```bash
wrangler kv:key put --namespace USAGE apikey:<KEY> 0 --local  # dev
wrangler kv:key delete --namespace USAGE apikey:<KEY>
```

### B) Exfiltration of Pro Data
**Signal:** Large portions of Pro translations leaked; unique canaries detected.

**Actions:**
1. Confirm canary hits; scope leak.
2. Block offending keys and sessions.
3. Send takedown notice citing proprietary license (`LICENSE_DATA.md`).
4. Rotate sample keys; update Release notes.

### C) Origin Exposure Attempt
**Signal:** Origin hit without shield; Worker logs show 403/401 from origin.

**Action:** Ensure backend and Worker use the **same** `EDGE_SHIELD_TOKEN`; enforce in origin middleware.

### D) Stripe Replay / Signature Failure
**Signal:** 400 “signature verification failed”.

**Action:** Verify prod mode and `whsec_…` secret; rotate and redeploy if compromised.

### E) GPT Misuse / Cost Spike
**Signal:** Surge of 404→200 (GPT) misses; high OpenAI usage; repeated novel phrases.

**Actions:**
1. Disable fallback temporarily:
   ```bash
   flyctl secrets set -a dhkalign-backend ENABLE_GPT_FALLBACK='0'
   cd ~/Dev/dhkalign && flyctl deploy -a dhkalign-backend
   ```
2. Lower caps: reduce `GPT_MAX_TOKENS`, increase `GPT_TIMEOUT_MS`, or set `GPT_RETRIES=0`.
3. Inspect keys generating most GPT misses; throttle or re-key.
4. Seed packs with frequent GPT phrases to reduce misses.

**Follow-up:** Add monitoring for `db_hit`, `gpt_fallback`, and `gpt_fail` counts; alert on spikes.

---

## 4) Incident Runbooks

### Free 530 (Worker → Origin Upstream)
```bash
curl -is https://backend.dhkalign.com/health | sed -n '1,2p'
cloudflared tunnel run dhkalign-origin  # or --protocol http2
```

### Origin 403 (Shield)
```bash
cd infra/edge
wrangler secret put EDGE_SHIELD_TOKEN --env production
wrangler deploy --env production
# restart backend with same EDGE_SHIELD_TOKEN
```

### Stripe Signature Failure
```bash
cd infra/edge
wrangler secret put STRIPE_WEBHOOK_SECRET --env production  # paste whsec_…
wrangler deploy --env production
```

### Admin Not Locked
Ensure global guard in Worker:
```js
if (url.pathname.startsWith('/admin/')) {
  const got = request.headers.get('x-admin-key') || '';
  if (!env.ADMIN_KEY || got !== env.ADMIN_KEY) {
    return json({ error: 'unauthorized' }, 401);
  }
}
```

See also Security Runbook → G) Pro returns 404 on a miss (fallback expected).

---

## 5) Evidence & Audit

- KV footprints: `usage:<key>:<YYYY-MM-DD>`, `session_to_key:<sessionId>`, `apikey:<key>`, `apikey.meta:<key>`, `stripe_evt:<eventId>`.
- Logs: Worker tail (prod), origin ASGI logs (no full text), tunnel logs. Retain security/audit logs ≤ 180 days.
- Backups: run `scripts/backup_db.sh`; verify restores quarterly.

---

## 6) Legal Posture

- **Code (MIT):** permissive reuse; retain attribution.
- **Data (Proprietary):** no redistribution, scraping; DMCA/takedown for leaks.
- **ToS:** prohibit key sharing, scraping, and automated bulk extraction.

---

## 7) On-call Smoke Tests

```bash
# Worker & origin health
curl -is https://<WORKER_HOST>/edge/health | sed -n '1,2p'
curl -is https://backend.dhkalign.com/health | sed -n '1,2p'

# Free (POST + GET)
curl -is -X POST https://<WORKER_HOST>/translate -H 'content-type: application/json' -d '{"text":"Bazar korbo"}' | sed -n '1,2p'
curl -is 'https://<WORKER_HOST>/translate?q=Bazar%20korbo' | sed -n '1,2p'

# Stripe bad signature
curl -is -X POST https://<WORKER_HOST>/webhook/stripe -H 'stripe-signature: test' -d '{}' | sed -n '1,3p'
```

---

## 8) Contacts

- Ops & Security: **admin@dhkalign.com**
- Legal notices: **admin@dhkalign.com** (subject: _Takedown Notice_)