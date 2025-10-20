# DHK Align — Property Defense & Abuse Response (Oct 2025)

_This policy explains how DHK Align protects code, data, and runtime property; detects abuse; and executes runbooks. It complements `README.md`, `docs/ARCHITECTURE.md`, `docs/OPS.md`, `docs/PRIVACY.md`, and `docs/API.md`._

---

## 0) Golden Invariants

- **Edge‑only ingress**: Clients call the **Cloudflare Worker**; only the Worker calls private origins with `x-edge-shield`. Clients never send this header.  
- **Admin guard**: All `/admin/*` endpoints require `x-admin-key`.  
- **Free routes**: `GET /api/translate?q=…`, `POST /translate` (`{"text":"…"}` primary).  
- **Pro route**: `POST /translate/pro` at Edge requires `x-api-key`; origin trusts requests that include a valid `x-edge-shield`.  
- **Fallback (optional)**: DB‑first → GPT fallback on miss → auto‑insert → subsequent calls hit DB.  
- **Quotas & rate limits**: Edge enforces per‑key daily quotas (KV). Origin can enforce 60/min per IP when enabled.  
- **One‑time key handoff**: `GET /billing/key?session_id=…` returns once; origin allowlisted.  
- **No text storage by default**: Edge does not persist translation text; origin logs avoid full text.  
- **DB identity invariant**: Uniqueness on `(src_lang, roman_bn_norm, tgt_lang, pack)`; `id` cosmetic. SQLite at `backend/data/translations.db`.  
- **Licenses**: Code = MIT; Data = Proprietary. See `LICENSE`, `LICENSE_CODE.md`, `LICENSE_DATA.md`, and `docs/THIRD_PARTY_NOTICES.md`.

---

## 1) Property Surfaces & Protections

### A) Code
- **Secrets**: Never committed. Dev in `infra/edge/.dev.vars`; prod via Wrangler/Cloudflare; backend via Fly secrets.  
- **Branches**: Commit signing + protected branches.  
- **Scanning**: `bandit -r backend/` (Python); CodeQL on repo (non‑blocking in speed mode).  
- **Artifacts**: No virtualenvs (`backend/.venv/`) or DB files in git.

### B) Data (Proprietary)
- **Access**: Only via Edge; Pro requires `x-api-key`. No public dumps.  
- **Ingest**: `normalize_jsonl.py → import_clean_jsonl.py` with provenance; dedupe by invariant key.  
- **Watermarking (planned)**: low‑impact canary pairs per pack to trace leaks.

### C) Runtime (Edge + Origins)
- **Gates**: `x-api-key` on `/translate/pro`; `x-admin-key` on `/admin/*`.  
- **Shield**: Worker injects `x-edge-shield`; origins reject requests without it.  
- **Quotas**: KV daily per‑key; 429 on exceed.  
- **CORS/CSP**: allowlist production origins; explicit dev hosts `127.0.0.1:5173` (Vite), `127.0.0.1:8789` (Worker dev).  
- **Caching**: Edge KV (`CF-Cache-Edge: HIT|MISS`); origin TTL (`X-Backend-Cache: HIT|MISS`); bypass with `?cache=no`.  
- **Stripe**: Signature verify (5‑minute tolerance), event allowlist (`checkout.session.completed`), KV replay lock; API keys stored as `apikey:<key> = "1"`, metadata under `apikey.meta:<key>`.  
- **Fallback controls**: If enabled, origin calls OpenAI (default `gpt-4o-mini`) with strict limits; first miss auto‑inserts a pro row.

---

## 2) GPT Fallback (Optional)

Enable fallback to serve Pro DB misses via OpenAI and auto‑insert results (Fly secrets; do **not** commit secrets):

```bash
flyctl secrets set -a dhkalign-backend \
  OPENAI_API_KEY='sk-…' \
  ENABLE_GPT_FALLBACK='1' \
  GPT_MODEL='gpt-4o-mini' \
  GPT_MAX_TOKENS='128' \
  GPT_TIMEOUT_MS='2000'
flyctl deploy -a dhkalign-backend
```

First miss returns `"source":"gpt"`; repeats return `"source":"db"`.

---

## 3) Abuse Taxonomy → Signals → Responses

### A) Key sharing / bulk scraping
**Signals**: bursts across many IPs on one key; daily quota hits; cache anomalies.  
**Response**:
1. Throttle or pause key; notify user.  
2. Mint replacement; disable old (`apikey:<old>` → `0`); rotate.  
3. If persistent, suspend per ToS.

**KV ops (dev)**:
```bash
wrangler kv:key put --namespace USAGE apikey:<KEY> 0 --local
wrangler kv:key delete --namespace USAGE apikey:<KEY> --local
```

### B) Exfiltration of Pro data
**Signals**: canary hits in the wild; mirrored corpus.  
**Response**:
1. Confirm canary; scope leak.  
2. Revoke keys; block sessions; rate‑limit ASNs.  
3. Takedown citing proprietary data license; update release notes; rotate samples.

### C) Origin exposure attempt
**Signals**: origin hit without shield; 401/403 from origin; Worker logs show direct hits.  
**Response**: ensure Worker and origin share `EDGE_SHIELD_TOKEN`; enforce in origin middleware; validate CF DNS (orange cloud/Tunnel).

### D) Stripe replay / signature failure
**Signals**: 400 “signature verification failed”.  
**Response**: verify prod mode, correct `whsec_…`; rotate if compromised; confirm KV replay lock.

### E) GPT misuse / cost spike
**Signals**: surge of 404→200 (gpt) misses; rapid novel phrases; OpenAI usage spike.  
**Response**:
1. Temporarily disable fallback:
   ```bash
   flyctl secrets set -a dhkalign-backend ENABLE_GPT_FALLBACK='0'
   flyctl deploy -a dhkalign-backend
   ```
2. Lower caps: reduce `GPT_MAX_TOKENS`, increase `GPT_TIMEOUT_MS`; set retries to 0.  
3. Identify abusive keys; throttle or re‑key; seed packs with repeated GPT phrases.

---

## 4) Incident Runbooks

**Edge 5xx spike (version fails)**  
- Check Smoke on main.  
- Cloudflare → WAF → Rules: ensure no rule blocks `/version`.

**Origin 403 (shield)**  
```bash
# Worker
cd infra/edge && wrangler secret put EDGE_SHIELD_TOKEN --env production && wrangler deploy --env production
# Origin (Fly)
flyctl secrets set -a dhkalign-backend EDGE_SHIELD_TOKEN='<same>' && flyctl deploy -a dhkalign-backend
```

**Stripe signature failure**  
```bash
cd infra/edge && wrangler secret put STRIPE_WEBHOOK_SECRET --env production && wrangler deploy --env production
```

**Admin not locked** (Worker guard)
```js
if (url.pathname.startsWith('/admin/')) {
  const got = request.headers.get('x-admin-key') || '';
  if (!env.ADMIN_KEY || got !== env.ADMIN_KEY) return json({ error: 'unauthorized' }, 401);
}
```

---

## 5) Evidence & Audit

- **KV footprints**: `usage:<key>:<YYYY-MM-DD>`, `session_to_key:<sessionId>`, `apikey:<key>`, `apikey.meta:<key>`, `stripe_evt:<eventId>`.  
- **Logs**: Worker tail (prod), origin ASGI logs (no full text), Tunnel logs. Retain security/audit logs ≤ 180 days.  
- **Backups**: `scripts/backup_db.sh` (manual). Verify restores quarterly. Future: Litestream/LiteFS.

---

## 6) Legal Posture

- **Code**: MIT (retain attribution).  
- **Data**: Proprietary (no redistribution/scraping). Use takedown for leaks.  
- **Notices**: Keep `docs/THIRD_PARTY_NOTICES.md` in repo and ship with public images.

---

## 7) On‑call Smoke Tests

```bash
# Edge & origin health (prod)
curl -is https://edge.dhkalign.com/edge/health   | sed -n '1,2p'
curl -is https://backend.dhkalign.com/health     | sed -n '1,2p'

# Free (through Edge)
curl -is 'https://edge.dhkalign.com/api/translate?q=Rickshaw%20pabo%20na' | sed -n '1,2p'

# Stripe bad signature
curl -is -X POST https://edge.dhkalign.com/webhook/stripe \
  -H 'stripe-signature: test' -d '{}' | sed -n '1,3p'
```

---

## 8) Contacts

- Ops & Security: **admin@dhkalign.com**  
- Legal notices: **admin@dhkalign.com** (subject: _Takedown Notice_)