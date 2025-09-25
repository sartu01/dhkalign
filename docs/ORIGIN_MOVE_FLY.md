# Origin Move — Fly.io Rollout (DHK Align)

This runbook moves the FastAPI origin onto **Fly.io**, while the Edge Worker continues to call the origin via **Cloudflare** (`https://backend.dhkalign.com`).

---

## 1) Prereqs
- flyctl installed: `curl -L https://fly.io/install.sh | sh`
- Logged in: `flyctl auth login`
- Repo root: `~/Dev/dhkalign` (contains `Dockerfile` and `fly.toml`)

---

## 2) One‑time app setup (if not already created)
```bash
APP=dhkalign-backend
REGION=iad

# create the app if missing
flyctl apps list | grep -q "^$APP" || flyctl apps create "$APP"

# volume for SQLite at /app/backend/data
flyctl volumes create dhkalign_data --region "$REGION" --app "$APP" --size 1
```

---

## 3) Secrets (required & optional)
**Shield (required)** — must match Worker:
```bash
flyctl secrets set -a dhkalign-backend EDGE_SHIELD_TOKEN='<same-token-as-worker-prod>'
```

**GPT fallback (optional)** — auto‑fill misses once, then DB hit:
```bash
flyctl secrets set -a dhkalign-backend \
  OPENAI_API_KEY='sk-...' \
  ENABLE_GPT_FALLBACK='1' \
  GPT_MODEL='gpt-4o-mini' \
  GPT_MAX_TOKENS='128' \
  GPT_TIMEOUT_MS='2000'
```

---

## 4) Deploy
```bash
cd ~/Dev/dhkalign
flyctl deploy -a dhkalign-backend --remote-only
```

---

## 5) DNS (Cloudflare)
- **CNAME** `backend.dhkalign.com` → `dhkalign-backend.fly.dev` (**Proxied** / orange cloud).
- SSL/TLS mode: **Full (Strict)**.

Sanity:
```bash
curl -is https://backend.dhkalign.com/health | sed -n '1,2p'
```

> If issuing the Fly cert: temporarily set DNS to **DNS only** (grey cloud) until Fly shows **Ready**, then flip back to **Proxied**.

---

## 6) Seed SQLite on Fly (first time)
```bash
# ensure dir exists and remove any bad file
flyctl ssh console -a dhkalign-backend -C 'mkdir -p /app/backend/data && rm -f /app/backend/data/translations.db'

# upload your local DB (binary‑safe, single line)
cat "$HOME/Dev/dhkalign/backend/data/translations.db" | \
  flyctl ssh console -a dhkalign-backend --command "sh -lc 'cat > /app/backend/data/translations.db && sync'"

# verify header + row count
flyctl ssh console -a dhkalign-backend -C \
"python -c \"import os,sqlite3; p='/app/backend/data/translations.db'; print('size:',os.path.getsize(p)); print('rows:', sqlite3.connect(p).execute('select count(*) from translations').fetchone()[0])\""
```

Expected:
```
size: <positive bytes>
rows: <positive number>  # e.g., 279
```

---

## 7) Smoke tests (prod)
```bash
# origin (through Cloudflare → Fly)
curl -is https://backend.dhkalign.com/health | sed -n '1,2p'

# worker free (DB)
WORKER="https://dhkalign-edge-production.tnfy4np8pm.workers.dev"
curl -is "$WORKER/translate?q=Rickshaw%20pabo%20na" | sed -n '1,2p'

# worker pro (use a real prod key)
KEY="<PROD_API_KEY>"  # mint via /admin/keys/add
curl -is -X POST "$WORKER/translate/pro" \
  -H 'content-type: application/json' -H "x-api-key: $KEY" \
  -d '{"text":"pocket khali, ki korbo","src_lang":"bn-rom","tgt_lang":"en"}' | sed -n '1,20p'
```

If fallback is enabled and the phrase is not in DB, the first call returns `source:"gpt"`; repeat with the same text returns `source:"db"`.

---

## 8) Troubleshooting quickies
- **502 via CF, Fly 200** → Cloudflare SSL/TLS mode or CNAME not proxied. Set **Full (Strict)**, ensure proxied CNAME.
- **401 on /translate/pro** → shield mismatch. Set the same `EDGE_SHIELD_TOKEN` on Fly & Worker, redeploy both.
- **404 on pro miss** → fallback disabled or missing OpenAI key. Set secrets (see §3) and redeploy.
- **“file is not a database”** → re‑upload DB exactly as in §6 (single‑line pipe), then verify header + rows.

---

## 9) Rollback
- Re‑deploy previous image: `flyctl releases -a dhkalign-backend` → `flyctl deploy -i <IMAGE>`
- Toggle fallback off: `flyctl secrets set -a dhkalign-backend ENABLE_GPT_FALLBACK='0' && flyctl deploy -a dhkalign-backend`

