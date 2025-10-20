# DHK Align — Public API (Oct 2025)

Hardened **Cloudflare Edge** in front; origins stay private.  
Clients **never** call origins directly and **never** send `x-edge-shield`.

---

## Base URLs

- **Edge (prod)**: `https://edge.dhkalign.com`  
- **Origin (private; Worker only)**: `https://backend.dhkalign.com`

> In examples we use `https://edge.dhkalign.com`. In dev, point `REACT_APP_API_BASE_URL` to your local Worker (e.g., `http://127.0.0.1:8789`).

---

## Auth & Headers

| Flow   | Where | Header(s)                         |
|--------|-------|-----------------------------------|
| Free   | Edge  | _none_                            |
| Pro    | Edge  | `x-api-key: <API_KEY>`            |
| Admin  | Edge  | `x-admin-key: <ADMIN_KEY>`        |

- Clients **do not** send `x-edge-shield`. The Worker injects it when calling origin.
- Content type for POST JSON: `Content-Type: application/json; charset=utf-8`

---

## Endpoints (Edge)

| Method | Path                         | Purpose                                   |
|--------|------------------------------|-------------------------------------------|
| GET    | `/edge/health`               | Edge health                               |
| GET    | `/version`                   | Build SHA                                 |
| GET    | `/api/translate?q=…`         | **Free** translate (DB-first)             |
| POST   | `/translate`                 | **Free** translate (JSON body)            |
| POST   | `/translate/pro`             | **Pro** translate (key-gated)             |
| GET    | `/billing/key?session_id=…`  | One-time API key handoff after checkout   |
| GET    | `/admin/health`              | Admin: health                             |
| GET    | `/admin/cache_stats`         | Admin: cache stats                        |
| GET    | `/admin/whoami`              | Admin: current environment/identity       |
| GET    | `/admin/keys/add?key=…`      | Admin: add API key                        |
| GET    | `/admin/keys/check?key=…`    | Admin: check API key                      |
| GET    | `/admin/keys/del?key=…`      | Admin: delete API key                     |

---

## Free — GET `/api/translate`

**Query**
- `q` (string, required) — input text in Banglish or English  
- `src_lang` (optional; default auto) — `"bn-rom"` or `"en"`  
- `tgt_lang` (optional; default auto) — `"en"` or `"bn-rom"`

**Response**
```json
// 200 OK
{
  "ok": true,
  "data": {
    "src": "kemon acho",
    "tgt": "how are you",
    "src_lang": "bn-rom",
    "tgt_lang": "en",
    "source": "db"
  }
}
```

**Examples**
```bash
curl -s "https://edge.dhkalign.com/api/translate?q=Rickshaw%20pabo%20na" | jq
curl -s "https://edge.dhkalign.com/api/translate?q=valo%20achi&src_lang=bn-rom&tgt_lang=en" | jq
```

---

## Free — POST `/translate`

**Body**
```json
{ "q": "Bazar korbo", "src_lang": "bn-rom", "tgt_lang": "en" }
```

**Response** — same shape as GET.

**Example**
```bash
curl -sX POST "https://edge.dhkalign.com/translate" \
  -H 'content-type: application/json; charset=utf-8' \
  -d '{"q":"Bazar korbo","src_lang":"bn-rom","tgt_lang":"en"}' | jq
```

---

## Pro — POST `/translate/pro`

**Headers**
- `x-api-key: <API_KEY>`

**Body**
```json
{ "q": "pocket khali, ki korbo", "src_lang": "bn-rom", "tgt_lang": "en" }
```

**Response**
```json
// 200 OK
{
  "ok": true,
  "data": {
    "src": "pocket khali, ki korbo",
    "tgt": "my pockets are empty, what should I do",
    "src_lang": "bn-rom",
    "tgt_lang": "en",
    "source": "db",         // or "gpt" on first miss when fallback is enabled
    "pack": "slang"         // present if a specific pack was used
  }
}
```

**Example**
```bash
KEY="<PROD_API_KEY>"
curl -sX POST "https://edge.dhkalign.com/translate/pro" \
  -H 'content-type: application/json; charset=utf-8' \
  -H "x-api-key: $KEY" \
  -d '{"q":"pocket khali, ki korbo","src_lang":"bn-rom","tgt_lang":"en"}' | jq
```

---

## Billing — GET `/billing/key`

One-time key handoff after successful Stripe checkout.  
**Query**: `session_id` (required)

**Response**
```json
// 200 OK
{ "ok": true, "data": { "api_key": "prod_..." } }

// 404
{ "ok": false, "error": "not_found" }
```

> Origin-allowlisted. Not for public use.

---

## Admin (GET)

**Headers**: `x-admin-key: <ADMIN_KEY>`

```bash
curl -s -H "x-admin-key: $ADMIN" "https://edge.dhkalign.com/admin/health" | jq
curl -s -H "x-admin-key: $ADMIN" "https://edge.dhkalign.com/admin/cache_stats" | jq
curl -s -H "x-admin-key: $ADMIN" "https://edge.dhkalign.com/admin/whoami" | jq
ADMIN='<ADMIN_KEY>'
curl -s -H "x-admin-key: $ADMIN" "https://edge.dhkalign.com/admin/keys/add?key=prod_demo_123" | jq
curl -s -H "x-admin-key: $ADMIN" "https://edge.dhkalign.com/admin/keys/check?key=prod_demo_123" | jq
curl -s -H "x-admin-key: $ADMIN" "https://edge.dhkalign.com/admin/keys/del?key=prod_demo_123" | jq
```

---

## CORS, Cache, Shield

- **CORS (prod)**: `https://dhkalign.com`, `https://www.dhkalign.com`  
  **Dev**: `http://127.0.0.1:5173` (or your local dev host)
- **Edge cache header**: `CF-Cache-Edge: HIT|MISS`  
  **Bypass** with `?cache=no`
- **Origin cache header**: `X-Backend-Cache: HIT|MISS` (visible when edge bypassed)
- **Shield**: `x-edge-shield` is **Worker → origin** only; clients never send it.

---

## Errors (canonical)

| HTTP | Body.error                 |
|------|----------------------------|
| 400  | `missing_query` \| `invalid_json` |
| 401  | `invalid_api_key`          |
| 404  | `not_found`                |
| 415  | `unsupported_media_type`   |
| 429  | `rate_limited`             |

---

## Status / Version

- `GET /edge/health` → `{ ok:true, ts, env }`
- `GET /version` → `{ sha: "<git_sha>" }`

---

## Notes

- Free path prefers DB; Pro path is DB‑first with optional GPT fallback (first **gpt**, repeat **db**).
- Keep API keys secret; rotate if leaked.
- Quotas are enforced at Edge (per key and IP).