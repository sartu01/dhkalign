# DHK Align — Property Defense & Abuse Response

_Last updated: 2025‑09‑22_

This document captures how we protect DHK Align’s code, data, and runtime property; how we detect and respond to abuse; and the exact runbooks to use. It aligns with `README.md`, `docs/SECURITY.md`, `docs/ARCHITECTURE.md`, `docs/PRIVACY.md`, and `docs/EXECUTION_DELIVERABLES.md`.

---

## 0) Golden invariants (do not drift)
- **Edge‑only ingress.** Clients call the **Cloudflare Worker**; only the Worker calls the private origin with the **internal** header `x‑edge‑shield`. Clients never send this header.
- **Admin guard.** All `/admin/*` endpoints require `x‑admin-key`.
- **Free route.** `/translate` supports **POST `{"text":"…"}`** (canonical) **and** **GET `?q=`**.
- **Pro route.** `/translate/pro` at the **Edge** requires `x‑api-key`; origin trusts only the shield.
- **Quotas & RL.** Edge daily per‑key quota (KV). Origin SlowAPI 60/min **only when enabled**.
- **One‑time key handoff.** `/billing/key?session_id=…` returns once and is origin‑allowlisted.
- **No text storage by default.** We do not store translation text at the edge; origin logs avoid full text.
- **Identity invariant (DB).** Uniqueness on *(src_lang, roman_bn_norm, tgt_lang, pack)*. `id` is cosmetic. Runtime DB: `backend/data/translations.db`.
- **Licenses.** Code = MIT. Data = Proprietary. (See `LICENSE_CODE.md`, `LICENSE_DATA.md`.)

---

## 1) Property surface & protections

### Code
- **Repo hygiene.** No secrets in git. Dev secrets in `infra/edge/.dev.vars`; prod secrets via Wrangler.
- **Commit signing** on protected branches.
- **Scanning.** `bandit -r backend/` before PR merge.

### Data (proprietary)
- **Access path:** only through the Edge (Pro = API key). No public dumps.
- **De‑dup + provenance:** invariant key `(src_lang, roman_bn_norm, tgt_lang, pack)`; import pipeline `normalize_jsonl.py → import_clean_jsonl.py` establishes provenance.
- **Optional watermarking (planned):** embed low‑impact canary pairs per pack to trace exfiltration.

### Runtime (Edge + Origin)
- **Gating.** `x‑api‑key` (Edge /translate/pro), global `x‑admin‑key` guard on `/admin/*`.
- **Shield.** `x‑edge‑shield` added by Worker → origin; origin rejects Pro without it.
- **Quotas.** KV daily per‑key quota (e.g., 1000/day) → **429**.
- **CORS/CSP.** Allowlist origins; Stripe host allowed; dev hosts explicit (`127.0.0.1:5173`, `127.0.0.1:8789`).
- **Caching.** Edge KV (`CF‑Cache‑Edge: HIT|MISS`); origin TTL (`X‑Backend‑Cache: HIT|MISS`), bypass with `?cache=no`.
- **Stripe.** Signature check (5‑min tolerance), event allowlist (`checkout.session.completed`), KV replay lock; key mint to `apikey:<key>` = "1", metadata at `apikey.meta:<key>`.

---

## 2) Abuse taxonomy → responses

### A) Key sharing / bulk scraping
**Signal:** Traffic bursts from many IPs using one key; daily quota hits; unusual cache patterns.

**Immediate actions:**
1. **Throttle key**: temporarily lower quota for that key; alert user.
2. **Re‑key**: mint a replacement; disable old key (`USAGE.del apikey:<old>` or set flag to 0); update user.
3. **TOS notice**: if continued abuse, suspend key per policy.

**KV ops:**
```bash
# disable key quickly (edge won’t accept non‑"1")
wrangler kv:key put --namespace USAGE apikey:<KEY> 0 --local  # dev
# or delete
wrangler kv:key delete --namespace USAGE apikey:<KEY>
```

### B) Exfil of pro data
**Signal:** Large portions of Pro translations appear elsewhere; unique canaries found.

**Immediate actions:**
1. **Confirm canary hits** (if watermarking enabled) and scope the leak.
2. **Block offending keys** and associated sessions.
3. **Legal**: send takedown notice citing proprietary license (`LICENSE_DATA.md`).
4. **Rotate** any shared sample keys; update Release notes.

### C) Origin exposure attempt
**Signal:** Origin hit without shield; Worker tail shows 403/401 from origin.

**Immediate:** ensure the backend and Worker use the **same** `EDGE_SHIELD_TOKEN`. Enforce at origin middleware.

### D) Stripe replay / signature failure
**Signal:** 400 “signature verification failed”.

**Immediate:**
- Verify prod endpoint mode (Test vs Live) and `whsec_…` value.
- Rotate secret if compromised; set new secret in Worker; redeploy.

---

## 3) Incident runbooks (copy‑paste)

### Free 530 (Worker → origin upstream)
```bash
# confirm origin
curl -is https://backend.dhkalign.com/health | sed -n '1,2p'
# tunnel on backend host
cloudflared tunnel run dhkalign-origin  # or --protocol http2
```

### Origin 403 (shield)
```bash
cd infra/edge
wrangler secret put EDGE_SHIELD_TOKEN --env production
wrangler deploy --env production
# restart backend with same EDGE_SHIELD_TOKEN
```

### Stripe signature fail
```bash
cd infra/edge
wrangler secret put STRIPE_WEBHOOK_SECRET --env production  # paste whsec_…
wrangler deploy --env production
```

### Admin not locked
Ensure global guard in Worker:
```js
if (url.pathname.startsWith('/admin/')) {
  const got = request.headers.get('x-admin-key') || '';
  if (!env.ADMIN_KEY || got !== env.ADMIN_KEY) {
    return json({ error: 'unauthorized' }, 401);
  }
}
```

---

## 4) Evidence & audit
- **KV footprints:** `usage:<key>:<YYYY‑MM‑DD>`, `session_to_key:<sessionId>`, `apikey:<key>`, `apikey.meta:<key>`, `stripe_evt:<eventId>`.
- **Logs:** Worker tail (prod), origin ASGI logs (no full text), tunnel logs. Keep security/audit logs ≤ 180 days.
- **Backups:** run `scripts/backup_db.sh`; verify restores quarterly.

---

## 5) Legal posture (summary)
- **Code (MIT)**: permissive reuse; keep attribution.
- **Data (Proprietary)**: no redistribution/scraping; DMCA/takedown for leaks.
- **ToS**: prohibit sharing keys, scraping, and automated bulk extraction.

---

## 6) On‑call smoke
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

## 7) Contacts
- Ops & Security: **admin@dhkalign.com**
- Legal notices: **admin@dhkalign.com** (subject: _Takedown Notice_)