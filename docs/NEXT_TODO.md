# Next To‑Do (Iron‑Clad Phase)

## 1) Edge Shield (Cloudflare Worker + KV)
**Goal:** All traffic is routed through the Cloudflare Worker at `infra/edge/src/index.js`. The worker enforces access control, rate limits, and proxies requests to the private backend. The `wrangler.toml` config includes KV namespaces for `CACHE` and `USAGE` and secrets for `EDGE_SHIELD_TOKEN` and `ADMIN_KEY`.

Setup:
```bash
# work tab
npm i -g wrangler
cd ~/Dev/dhkalign/infra/edge
# Configure wrangler.toml with:
# - kv_namespaces = [{ binding = "CACHE", id = "..." }, { binding = "USAGE", id = "..." }]
# - [vars] with EDGE_SHIELD_TOKEN and ADMIN_KEY secrets set
wrangler publish
```

Smoke test after DNS is pointed:
```bash
curl -s https://dhkalign.com/health | jq .
```

---

## 2) Admin Health & Cache Stats (ops eyes without SSH)
**Goal:** `/admin/health` and `/admin/cache_stats` endpoints are available both via the edge and backend, gated by the `x-admin-key` header matching the `ADMIN_KEY` secret.

Test:
```bash
curl -s https://dhkalign.com/admin/health -H "x-admin-key: $ADMIN_KEY" | jq .
curl -s https://dhkalign.com/admin/cache_stats -H "x-admin-key: $ADMIN_KEY" | jq .
```

---

## 3) Response Cache (reduce duplicate DB hits)
**Goal:** Two-layer caching strategy:
- Edge KV cache with `CACHE` namespace, indicated by `CF-Cache-Edge` headers.
- Backend in-process TTL cache with `X-Backend-Cache` headers.
Clients can bypass caches with `?cache=no`.

Quick check:
```bash
curl -s -X POST https://dhkalign.com/translate -H 'Content-Type: application/json' \
  -d '{"text":"kemon acho","src_lang":"banglish","dst_lang":"english"}' >/dev/null; time \
curl -s -X POST https://dhkalign.com/translate -H 'Content-Type: application/json' \
  -d '{"text":"kemon acho","src_lang":"banglish","dst_lang":"english"}' >/dev/null
```

---

## 4) Usage Tracker (revenue/abuse guardrails)
**Goal:** Usage counters are tracked per API key daily in the `USAGE` KV namespace with keys like `usage:{api_key}:{YYYYMMDD}`. Periodic export/import to `private/usage.db` for analytics and billing.

Check usage counts:
```bash
# Use a script or KV explorer to view usage counts per key and day
```

---

## 5) Docs + Rule Card (close clean)
- Update this file with what shipped.
- Generate **Rule Card** for the session (tabs discipline, paths, logs, backup time).
- Commit & push docs.

```bash
git add docs/NEXT_TODO.md backend/monitoring.py backend/cache_layer.py
git commit -m "ops: edge/admin/cache plan staged; monitoring + cache scaffolds"
```

---

## Later This Week (roadmap)
- DNS orange‑cloud → Worker front → origin private
- Add monthly rotation for `API_KEYS`, `ADMIN_KEY`, and `EDGE_SHIELD_TOKEN`
- Encrypted off‑box backup (manual): zip `private/backups/` to external drive
- Stripe integration and quota enforcement for `/translate/pro`
- Regression script: health + free + three pro packs → 200 JSON
