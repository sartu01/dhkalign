# Origin Move — Fly.io Rollout (DHK Align) · FastAPI origin behind Edge

This runbook moves the **FastAPI origin** to **Fly.io** while the **Cloudflare Worker** remains the single public ingress (origin stays private).

---

## 0) Ground truth / assumptions
- Repo root: `~/Dev/dhkalign`
- FastAPI Docker context: **`backend/`** (Dockerfile + fly.toml live here)
- Edge calls origin at: **`https://backend.dhkalign.com`**
- Health: `GET /health` (200 + JSON)
- Port: `8080`

> Keep the origin **private**. The Worker authenticates to origin via `x-edge-shield`.

---

## 1) Prereqs
```bash
# Fly CLI
curl -L https://fly.io/install.sh | sh
flyctl auth login
# Repo
cd ~/Dev/dhkalign/backend
```

---

## 2) One‑time app setup
```bash
APP=dhkalign-backend
ORG=personal           # your Personal org slug
REGION=iad

# create app if missing (org-aware)
flyctl apps list | awk -v a="$APP" '$1==a{f=1} END{exit !f}' || flyctl apps create "$APP" -o "$ORG"

# volume for SQLite at /app/backend/data (1GB; per-region)
flyctl volumes create dhkalign_data --region "$REGION" --app "$APP" --size 1
```

---

## 3) Secrets (required & optional)
**Edge‑Shield (required)** — must match the Worker:
```bash
flyctl secrets set -a "$APP" EDGE_SHIELD_TOKEN='<same-token-as-worker-prod>'
```

**GPT fallback (optional)** — auto‑fill misses once, then DB hit:
```bash
flyctl secrets set -a "$APP" \
  OPENAI_API_KEY='sk-...' \
  ENABLE_GPT_FALLBACK='1' \
  GPT_MODEL='gpt-4o-mini' \
  GPT_MAX_TOKENS='128' \
  GPT_TIMEOUT_MS='2000'
```

---

## 4) Deploy
From the **backend/** directory (where `Dockerfile` and `fly.toml` live):
```bash
cd ~/Dev/dhkalign/backend
flyctl deploy -a "$APP" --remote-only
```

**Scale cost‑guard**
```bash
# park when idle
flyctl scale count 0 -a "$APP"
# wake for testing
flyctl scale count 1 -a "$APP" && flyctl status -a "$APP"
```

**Logs / status**
```bash
flyctl status -a "$APP"
flyctl logs   -a "$APP"
```

---

## 5) DNS (Cloudflare)
- **CNAME** `backend.dhkalign.com` → `dhkalign-backend.fly.dev`
- **Proxy**: **ON** (orange cloud) for normal operation
- SSL/TLS: **Full (Strict)**

**If issuing the Fly cert**  
Temporarily set `backend.dhkalign.com` to **DNS only** (grey cloud) until `flyctl certs show backend.dhkalign.com -a "$APP"` shows **Ready**, then flip back to **Proxied**.

Sanity:
```bash
curl -is https://backend.dhkalign.com/health | sed -n '1,2p'
```

---

## 6) Seed SQLite on Fly (first time)
```bash
# ensure dir exists and remove any bad file
flyctl ssh console -a "$APP" -C 'mkdir -p /app/backend/data && rm -f /app/backend/data/translations.db'

# upload your local DB (binary‑safe, single line)
cat "$HOME/Dev/dhkalign/backend/data/translations.db" | \
  flyctl ssh console -a "$APP" --command "sh -lc 'cat > /app/backend/data/translations.db && sync'"

# verify header + row count
flyctl ssh console -a "$APP" -C \
"python - <<'PY'
import os, sqlite3
p='/app/backend/data/translations.db'
print('size:', os.path.getsize(p))
print('rows:', sqlite3.connect(p).execute('select count(*) from translations').fetchone()[0])
PY"
```

Expected:
```
size: <positive bytes>
rows: <positive number>  # e.g., 279
```

---

## 7) Smoke tests (prod)
```bash
# origin (CF → Fly)
curl -is https://backend.dhkalign.com/health | sed -n '1,2p'

# worker free (DB)
curl -is 'https://edge.dhkalign.com/api/translate?q=Rickshaw%20pabo%20na' | sed -n '1,2p'

# worker free (POST JSON)
curl -is -X POST 'https://edge.dhkalign.com/translate' \
  -H 'content-type: application/json' \
  -d '{"q":"Rickshaw pabo na"}' | sed -n '1,20p'

# worker pro (real prod key)
KEY="<PROD_API_KEY>"
curl -is -X POST 'https://edge.dhkalign.com/translate/pro' \
  -H 'content-type: application/json' -H "x-api-key: $KEY" \
  -d '{"q":"pocket khali, ki korbo","src_lang":"bn-rom","tgt_lang":"en"}' | sed -n '1,20p'
```

If fallback is enabled and the phrase is not in DB, the first call returns `"source":"gpt"`; repeat with the same text returns `"source":"db"`.

---

## 8) Troubleshooting quickies
- **502 via CF, Fly 200** → Cloudflare SSL/TLS mode or CNAME not proxied. Set **Full (Strict)**, ensure **Proxied** CNAME.
- **401 on /translate/pro** → shield mismatch. Set same `EDGE_SHIELD_TOKEN` on Fly & Worker; redeploy both.
- **404 on pro miss** → fallback disabled or missing OpenAI key. Set secrets (see §3) and redeploy.
- **“file is not a database”** → re‑upload DB exactly as in §6 (single‑line pipe), then verify header + rows.
- **Origin exposed** → ensure only the Worker can reach it (orange cloud/Tunnel; enforce `EDGE_SHIELD_ENFORCE=1`).

---

## 9) Rollback
- Re‑deploy previous image:
  ```bash
  flyctl releases -a "$APP"
  flyctl deploy -a "$APP" -i <IMAGE>
  ```
- Toggle fallback off:
  ```bash
  flyctl secrets set -a "$APP" ENABLE_GPT_FALLBACK='0'
  flyctl deploy -a "$APP"
  ```

---

## Appendix — Notes & gotchas
- Volumes are per‑region; keep `REGION` consistent.
- Keep `.env`, DB files, and anything under `private/` out of git.
- The Worker is the **only** public ingress; always go through edge in user‑facing flows.