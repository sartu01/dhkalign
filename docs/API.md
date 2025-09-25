# DHK Align API

**Base URLs**
- Prod Worker: `https://dhkalign-edge-production.tnfy4np8pm.workers.dev`
- Origin (private; used by Worker): `https://backend.dhkalign.com`

## Free: /translate
- **Methods**: `GET /translate?q=...`, `POST /translate` with JSON `{ "text": "...", "src_lang": "bn-rom", "tgt_lang": "en" }`
- **Auth**: none (free tier)
- **Response**:
  - 200 → `{ ok:true, data:{ src, tgt, src_lang, tgt_lang, source:"db" } }`
  - 400 → `{ ok:false, error:"missing_query"|"invalid_json" }`
  - 404 → `{ ok:false, error:"not_found" }`

**Examples**
```bash
# GET
curl -s "https://<WORKER_HOST>/translate?q=Bazar%20korbo" | jq

# POST
curl -sX POST "https://<WORKER_HOST>/translate" \
  -H 'content-type: application/json' \
  -d '{"text":"Bazar korbo","src_lang":"bn-rom","tgt_lang":"en"}' | jq
```

## Pro: /translate/pro
- **Auth**: header `x-api-key: <PROD_API_KEY>`
- **Body**: `{ "text":"...", "src_lang":"bn-rom", "tgt_lang":"en" }`
- **Order**: DB-first → GPT fallback (if enabled) → auto-insert → serve
- **Response**:
  - 200 → `{ ok:true, data:{ src, tgt, src_lang, tgt_lang, source:"db"|"gpt", pack } }`
  - 400 → `{ ok:false, error:"invalid_json" }`
  - 401 → `{ ok:false, error:"invalid api key" }`
  - 404 → `{ ok:false, error:"not_found" }`

**Example**
```bash
curl -sX POST "https://<WORKER_HOST>/translate/pro" \
  -H 'content-type: application/json' -H "x-api-key: <PROD_API_KEY>" \
  -d '{"text":"pocket khali, ki korbo","src_lang":"bn-rom","tgt_lang":"en"}' | jq
```

## Billing
- `GET /billing/key?session_id=...` — **one-time** key handoff after successful Stripe checkout.
  - Response 200 → `{ ok:true, data:{ api_key } }` (mapping is deleted after read)
  - 404 → `{ ok:false, error:"not_found" }`
  - Origin-allowlisted; not for public use.

## Admin
- Auth: header `x-admin-key: <ADMIN_KEY>`
- Endpoints (GET):
  - `/admin/keys/add?key=<value>` → `{ ok:true, key }`
  - `/admin/keys/check?key=<value>` → `{ key, enabled: true|false }`
  - `/admin/keys/del?key=<value>` → `{ ok:true, key }`

**Examples**
```bash
ADMIN='<ADMIN_KEY>'
curl -s -H "x-admin-key: $ADMIN" "https://<WORKER_HOST>/admin/keys/add?key=prod_demo_123" | jq
curl -s -H "x-admin-key: $ADMIN" "https://<WORKER_HOST>/admin/keys/check?key=prod_demo_123" | jq
curl -s -H "x-admin-key: $ADMIN" "https://<WORKER_HOST>/admin/keys/del?key=prod_demo_123" | jq
```
(Do not use ADMIN keys for /translate/pro.)

## Notes
- CORS: prod allows `https://dhkalign.com` and `https://www.dhkalign.com`; dev allows `http://127.0.0.1:5173`.
- Cache headers:
  - Edge: `CF-Cache-Edge: HIT|MISS`
  - Origin: `X-Backend-Cache: HIT|MISS` (bypass via `?cache=no`)
- Shield: clients never send `x-edge-shield`; the Worker adds it when calling the origin.
