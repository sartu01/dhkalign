# Next To‑Do (Iron‑Clad Phase)

## 1) Edge Shield (Cloudflare Worker + KV)
```bash
mkdir -p gateway
cat > gateway/worker.js <<'JS'
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (!url.hostname.endsWith("dhkalign.com")) return new Response("Forbidden", { status: 403 });
    const ua = request.headers.get("user-agent") || "";
    if (!ua || /bot|curl|python-requests|wget/i.test(ua)) return new Response("Denied", { status: 403 });
    const allowed = ["/health", "/translate", "/translate/pro"];
    if (!allowed.includes(url.pathname)) return new Response("Not Found", { status: 404 });
    const ip = request.headers.get("CF-Connecting-IP") || "unknown";
    const bucket = Math.floor(Date.now() / 60000);
    const key = `rate:${ip}:${bucket}`;
    const raw = await env.KV.get(key);
    const count = parseInt(raw || "0", 10);
    const LIMIT = url.pathname === "/translate/pro" ? 300 : 100;
    if (count >= LIMIT) return new Response("Too many requests", { status: 429 });
    await env.KV.put(key, String(count + 1), { expirationTtl: 90 });
    const backend = env.BACKEND_BASE;
    return fetch(backend + url.pathname, { method: request.method, headers: request.headers, body: request.method === "POST" ? request.body : null });
  }
}
JS
cat > gateway/wrangler.toml <<'TOML'
name = "dhkalign-core"
main = "gateway/worker.js"
compatibility_date = "2025-08-23"
kv_namespaces = [{ binding = "KV", id = "REPLACE_WITH_YOUR_KV_ID" }]
[vars]
BACKEND_BASE = "https://REPLACE_WITH_YOUR_PRIVATE_ORIGIN"
TOML


# Next To‑Do (Iron‑Clad Phase) — TOMORROW GAME PLAN

> Focus: **Edge shield → Admin health → Cache → Usage tracker → Docs/Rule Card**
> Repo: `~/Dev/dhkalign`  •  Server tab: `./scripts/run_server.sh`  •  Work tab: everything else

---

## 0) Pre-flight (5 min)
```bash
# server tab
cd ~/Dev/dhkalign && ./scripts/run_server.sh
# work tab
curl -s http://127.0.0.1:8090/health | jq .   # expect ok:true, safe_rows: 446
```

---

## 1) Edge Shield — Cloudflare Worker + KV (Protect origin)
**Goal:** All traffic hits CF Worker; only `/health`, `/translate`, `/translate/pro` reach origin. Origin is private.

```bash
# work tab
npm i -g wrangler
cd ~/Dev/dhkalign/gateway
wrangler kv:namespace create "KV" | tee /tmp/kv.txt
KV_ID=$(grep -Eo 'id = "[^"]+"' /tmp/kv.txt | awk -F'"' '{print $2}')
sed -i '' "s/REPLACE_WITH_YOUR_KV_ID/$KV_ID/" wrangler.toml
# edit wrangler.toml → set BACKEND_BASE=https://<your-private-origin-or-tunnel>
wrangler publish
```

Smoke test after DNS is pointed later:
```bash
curl -s https://dhkalign.com/health | jq .
```

---

## 2) Admin Health (ops eyes without SSH)
**Goal:** `/admin/health` shows totals, cache hits/misses, blocked, last backup time.

Scaffold:
```bash
# work tab
cat > backend/monitoring.py <<'PY'
from datetime import datetime
from threading import Lock
class Monitor:
    def __init__(self):
        self.m = {"requests":0,"blocked":0,"cache_hits":0,"cache_misses":0,
                  "started": datetime.utcnow().isoformat()+"Z",
                  "last_backup": None}
        self._lock = Lock()
    def inc(self, key):
        with self._lock:
            self.m[key] = self.m.get(key, 0) + 1
    def set(self, key, val):
        with self._lock:
            self.m[key]=val
    def snapshot(self):
        with self._lock:
            return dict(self.m)
monitor = Monitor()
PY
```
Wire into app (later we’ll increment counters around endpoints):
```bash
# work tab (append route)
cat >> backend/app_sqlite.py <<'PY'
from backend.monitoring import monitor
from fastapi import Header, HTTPException
@app.get("/admin/health")
def admin_health(x_api_key: str | None = Header(default=None)):
    import os
    if (x_api_key or "") not in (os.getenv("API_KEYS","")):
        raise HTTPException(status_code=403, detail="forbidden")
    return monitor.snapshot()
PY
```
Test:
```bash
KEY=$(grep '^API_KEYS=' backend/.env | cut -d= -f2)
curl -s http://127.0.0.1:8090/admin/health -H "x-api-key: $KEY" | jq .
```

---

## 3) Response Cache (reduce duplicate DB hits)
**Goal:** in‑process TTL cache for both free/pro.
```bash
# work tab
cat > backend/cache_layer.py <<'PY'
import time, hashlib
class TTLCache:
    def __init__(self, ttl=3600): self.ttl, self.store = ttl, {}
    def _k(self,t,s,d): return hashlib.md5(f"{t}:{s}:{d}".lower().encode()).hexdigest()
    def get(self,t,s,d):
        k=self._k(t,s,d); v=self.store.get(k)
        if v and time.time()-v[1] < self.ttl: return v[0]
    def set(self,t,s,d,r):
        k=self._k(t,s,d); self.store[k]=(r,time.time())
        if len(self.store)>10000:
            # remove oldest ~1000
            for k in list(self.store)[:1000]: self.store.pop(k, None)
PY
```
Wire (sketch): in `backend/app_sqlite.py` create `cache = TTLCache(ttl=3600)`; before returning DB result, try `cache.get(text, src, dst)`; after hit, `cache.set(...)`. Increment `monitor.cache_hits/misses` accordingly.

Quick check:
```bash
# same phrase twice → second should be near-instant
curl -s -X POST http://127.0.0.1:8090/translate -H 'Content-Type: application/json' \
  -d '{"text":"kemon acho","src_lang":"banglish","dst_lang":"english"}' >/dev/null; time \
curl -s -X POST http://127.0.0.1:8090/translate -H 'Content-Type: application/json' \
  -d '{"text":"kemon acho","src_lang":"banglish","dst_lang":"english"}' >/dev/null
```

---

## 4) Usage Tracker (revenue/abuse guardrails)
**Goal:** record `/translate/pro` calls by API key, soft‑limit later.
```bash
sqlite3 private/usage.db \
  "CREATE TABLE IF NOT EXISTS usage_log(id INTEGER PRIMARY KEY, api_key TEXT, ts DATETIME, endpoint TEXT);"
```
Hook in `pro_routes.py` (pseudo): insert `(api_key, now, '/translate/pro')` on each pro call.

Check:
```bash
sqlite3 private/usage.db "SELECT api_key,count(*) FROM usage_log GROUP BY api_key;"
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
- Add monthly rotation for `API_KEYS`; add `ADMIN_KEY` for `/admin/health`
- Encrypted off‑box backup (manual): zip `private/backups/` to external drive
- Regression script: health + free + three pro packs → 200 JSON
