MVP Security (Next 3 Weeks)

0) Config (env)
	•	File: backend/.env
	•	Keys to set now
CORS_ORIGINS=http://localhost:3000,https://dhkalign.com
API_KEYS=<generate one hex key for now>
AUDIT_HMAC_SECRET=<another random hex>
	•	Command to generate: openssl rand -hex 24

⸻

1) Input validation + sanitization + headers + rate limits
	•	File: backend/security_middleware.py
	•	Controls
	•	Strict JSON schema (text required, <= 1000 chars)
	•	Basic sanitization (strip SQL-ish tokens, path traversal)
	•	IP+fingerprint (UA/Accept/Language) rate limit: 60/min
	•	Failed‑attempt bans (5 bad in 5 min → temp ban)
	•	Security headers: HSTS, CSP, nosniff, frame‑deny, strict referrer
	•	Gate /translate/pro (later) by API key
	•	Status: drop‑in ready (we already drafted this).
	•	Hook: in backend/app_sqlite.py:
from .security_middleware import SecurityMiddleware
app.add_middleware(SecurityMiddleware)
2) DB hardening
	•	File: backend/app_sqlite.py
	•	Controls
	•	connect() helper with:
conn = sqlite3.connect(DB, timeout=5.0, isolation_level=None)
conn.execute("PRAGMA busy_timeout=5000")
conn.execute("PRAGMA journal_mode=WAL")
•	Always parameterized queries.
	•	Keep /translate serving safety_level ≤ 1 only.

⸻

3) Tamper‑evident audit log
	•	File: backend/scripts/secure_log.py
	•	Controls
	•	Append‑only JSONL at private/audit/security.jsonl
	•	HMAC on each entry using AUDIT_HMAC_SECRET
	•	Use in middleware on schema errors, temp bans, 401s:
from .scripts.secure_log import secure_log
secure_log("bad_request", {"ip": ip, "reason": "..."},"WARN")
secure_log("temp_ban", {"ip": ip},"ERROR")
4) Cloudflare Edge shield (free tier API)
	•	Files:
	•	gateway/worker.js (Worker)
	•	gateway/wrangler.toml
	•	Controls
	•	Block non‑dhkalign.com host access (no direct IP)
	•	KV minute‑bucket per‑IP rate limit (100/min default)
	•	UA challenge (block obvious bots/curl)
	•	Optional geo block list
	•	Forward only GET /health, POST /translate to private origin
	•	wrangler.toml (skeleton)
name = "dhkalign-core"
main = "gateway/worker.js"
compatibility_date = "2025-08-23"
kv_namespaces = [{ binding = "KV", id = "YOUR_KV_ID" }]

[vars]
BACKEND_BASE = "https://your-private-backend.example.com"
5) Safe cache export (free tier)
	•	File: backend/scripts/export_client_cache.py
	•	Control: only export rows with COALESCE(safety_level,1) <= 1
	•	Output: frontend/src/data/dhk_align_client.json
	•	Cron (later): nightly rebuild.

⸻

6) Tests (prove no leaks)
	•	Local
# Health
curl -s http://127.0.0.1:8090/health | jq .

# Safe phrase → 200 with dst
curl -s -X POST http://127.0.0.1:8090/translate \
  -H 'Content-Type: application/json' \
  -d '{"text":"kemon acho","src_lang":"banglish","dst_lang":"english"}' | jq .

# Oversized body → 413
python - <<'PY'
import requests, json
r=requests.post("http://127.0.0.1:8090/translate",
  headers={"Content-Type":"application/json"},
  data=json.dumps({"text":"x"*5001}))
print(r.status_code)
PY
	•	Leak checks
	•	Known slang/profanity phrase → 404 on /translate
	•	Cache file contains only safe rows:
7) “Soon” items (do after MVP launch)
	•	API key rotation + per‑key quotas (SQLite/KV counters; rotate monthly)
	•	Nightly encrypted DB backup (GPG + last‑7 retention)
	•	Cloudflare WAF rules (method allowlist, body size, known-bad ASNs)
	•	/translate/pro route (key-gated, pack allowlist)

⸻

8) GPT fallback guard (stub for when we add it)
	•	File: backend/gpt_guard.py
	•	check_prompt() for injection patterns
	•	sanitize_response() (strip secrets/system-y text)
	•	Per‑user token/day (simple in‑mem → KV later)
	•	Circuit breaker flag
	•	Policy: GPT outputs are never served raw; always inserted into DB with safety_level=2 pending review (or into pro path only).

⸻

9) Runbook (tiny)
	•	Logs: private/audit/security.jsonl (HMAC’ed)
	•	Backups: private/backups/YYYY-MM-DD_translations.db.gpg
	•	Rotate: API_KEYS monthly; AUDIT_HMAC_SECRET quarterly (with re‑sign window)
	•	Incident: temp ban IP in CF, rotate keys, export logs, snapshot DB, root‑cause, patch test, redeploy