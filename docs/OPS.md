

# DHK Align — OPS Playbook (Oct 2025)

**Purpose**: Day‑to‑day runbooks for the Edge, FastAPI origin (Fly), and Go sidecar.  
**Audience**: You (operator), future collaborators, and on‑call.

---

## 0) Ground Truth

- **Repo root**: `~/Dev/dhkalign`
- **Edge**: Cloudflare Worker (single public ingress)
- **Frontend**: Cloudflare Pages (SPA)
- **Origins (private)**:
  - **FastAPI** on Fly → CNAME: `backend.dhkalign.com` → `dhkalign-backend.fly.dev`
  - **Go sidecar** on Fly → `/go/*` (parity), **parked** by default
- **DB**: SQLite at `backend/data/translations.db` (safety ≤ 1 free, ≥ 2 pro)
- **Required checks on `main`**: `["Cloudflare Pages","smoke"]`

---

## 1) Quick Status

```bash
# Front door
curl -sI https://dhkalign.com | head -n1
curl -I "https://www.dhkalign.com/test?q=1"   # 301 → apex

# Edge + origin health
curl -fsS https://edge.dhkalign.com/version | jq
curl -fsS https://backend.dhkalign.com/health | jq

# Free translate (through Edge)
curl -fsS 'https://edge.dhkalign.com/api/translate?q=Rickshaw%20pabo%20na' | jq
```

### Free translate (POST variant)
```bash
curl -fsS -X POST 'https://edge.dhkalign.com/translate' \
  -H 'content-type: application/json' \
  -d '{"q":"Rickshaw pabo na"}' | jq
```

### Header sanity
```bash
curl -si 'https://edge.dhkalign.com/api/translate?q=Rickshaw%20pabo%20na' | sed -n '1,20p'
# Expect: CF-Cache-Edge: HIT|MISS (edge); if bypassing, origin may report X-Backend-Cache: HIT|MISS
```

### Admin quick checks
```bash
ADMIN='<ADMIN_KEY>'
curl -s -H "x-admin-key: $ADMIN" "https://edge.dhkalign.com/admin/health" | jq
curl -s -H "x-admin-key: $ADMIN" "https://edge.dhkalign.com/admin/cache_stats" | jq
curl -s -H "x-admin-key: $ADMIN" "https://edge.dhkalign.com/admin/whoami" | jq
```

---

## 2) Fly Ops (Go sidecar + FastAPI)

### 2.1 Determine app names
```bash
# Go sidecar
GO_APP="$(awk -F\" '/^app = /{print $2}' backend-go/fly.toml)"
# FastAPI origin (typical)
API_APP="dhkalign-backend"
```

### 2.2 Login, status, logs
```bash
flyctl auth whoami >/dev/null 2>&1 || flyctl auth login
flyctl status -a "$GO_APP" || true
flyctl logs   -a "$GO_APP" --since 10m || true

flyctl status -a "$API_APP" || true
flyctl logs   -a "$API_APP" --since 10m || true
```

### 2.3 Scale (cost guard)
```bash
# Park (scale to zero)
flyctl scale count 0 -a "$GO_APP" || true
flyctl scale count 0 -a "$API_APP" || true

# Wake (one tiny machine)
flyctl scale count 1 -a "$GO_APP" && flyctl status -a "$GO_APP"
flyctl scale count 1 -a "$API_APP" && flyctl status -a "$API_APP"
```

### 2.4 Rolling deploys
```bash
# Go sidecar (from backend-go/)
cd backend-go
COMMIT_SHA="$(git -C .. rev-parse --short HEAD || echo dev)"
BUILD_TIME="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
DEPS_SHA="$(shasum -a 256 go.mod | awk '{print $1}')-$(date +%s)"
flyctl deploy --remote-only -a "$GO_APP" \
  --build-arg COMMIT_SHA="$COMMIT_SHA" \
  --build-arg BUILD_TIME="$BUILD_TIME" \
  --build-arg DEPS_SHA="$DEPS_SHA" \
  --yes
cd -

# FastAPI origin (from backend/)
cd backend
flyctl deploy --remote-only -a "$API_APP" --yes
cd -
```

### 2.5 Rollback
```bash
flyctl releases -a "$API_APP"
flyctl deploy   -a "$API_APP" -i <IMAGE_DIGEST_OR_TAG>
```

---

## 3) CI / Checks

```bash
# Trigger smoke on current branch and watch
BRANCH="$(git rev-parse --abbrev-ref HEAD)"
gh workflow run ".github/workflows/smoke.yml" -r "$BRANCH" || true
RID=$(gh run list --workflow ".github/workflows/smoke.yml" --branch "$BRANCH" -L 1 \
      --json databaseId -q '.[0].databaseId' 2>/dev/null)
[ -n "$RID" ] && gh run watch "$RID" -i 5 || true

# Required contexts snapshot (main)
REPO="$(gh repo view --json nameWithOwner -q .nameWithOwner)"
MAIN="$(gh repo view --json defaultBranchRef -q .defaultBranchRef.name)"
gh api "/repos/$REPO/branches/$MAIN/protection" \
  --jq '{strict:(.required_status_checks.strict//false),contexts:(.required_status_checks.contexts//[])}'
```

**Speed mode**: `["Cloudflare Pages","smoke"]`  
**Iron‑clad (later)**: switch to `["Cloudflare Pages","Smoke / smoke"]` once all PR branches emit the canonical context.

---

## 4) DNS / TLS (Cloudflare)

- `backend.dhkalign.com` **CNAME** → `dhkalign-backend.fly.dev`
- Proxy **ON** (orange cloud); SSL/TLS **Full (Strict)**

**Fly cert issuance**  
Temporarily set **DNS only** (grey) until:
```bash
flyctl certs show backend.dhkalign.com -a "$API_APP"
# → Ready
```
then switch back to **Proxied**.

Sanity:
```bash
curl -is https://backend.dhkalign.com/health | sed -n '1,2p'
```

---

## 5) Secrets

```bash
# Edge Shield — must match Worker
flyctl secrets set -a "$API_APP" EDGE_SHIELD_TOKEN='<same_as_worker>'

# GPT fallback (optional)
flyctl secrets set -a "$API_APP" \
  OPENAI_API_KEY='sk-...' ENABLE_GPT_FALLBACK='1' \
  GPT_MODEL='gpt-4o-mini' GPT_MAX_TOKENS='128' GPT_TIMEOUT_MS='2000'
```

Worker secrets are managed via Wrangler (`infra/edge`) and Cloudflare dashboard.

### Worker secrets (Cloudflare)
- `ADMIN_KEY` — required for `/admin/*`
- `EDGE_SHIELD_TOKEN` — must match the origin
- `STRIPE_WEBHOOK_SECRET` — for `/webhook/stripe`
- `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY` — if billing is enabled

---

## 6) DB Ops (SQLite)

**Seed or replace DB on Fly (binary‑safe)**
```bash
# remove bad file and upload a fresh one
flyctl ssh console -a "$API_APP" -C 'mkdir -p /app/backend/data && rm -f /app/backend/data/translations.db'
cat "$HOME/Dev/dhkalign/backend/data/translations.db" | \
  flyctl ssh console -a "$API_APP" --command "sh -lc 'cat > /app/backend/data/translations.db && sync'"
```

**Verify header + rows**
```bash
flyctl ssh console -a "$API_APP" -C \
"python - <<'PY'
import os, sqlite3, json
p='/app/backend/data/translations.db'
print(json.dumps({
  'size': os.path.getsize(p),
  'rows': sqlite3.connect(p).execute('select count(*) from translations').fetchone()[0]
}))
PY"
```

**Backup (manual)**
```bash
TS="$(date -u +%Y%m%d-%H%M%S)"
flyctl ssh sftp get -a "$API_APP" /app/backend/data/translations.db "./backups/translations.$TS.db"
sha256sum "./backups/translations.$TS.db"
```

*Future*: Litestream or LiteFS for continuous backups.

---

## 7) Runbooks (incidents)

**Edge 5xx spike**
- Check Smoke on main; if Edge `/version` fails, Worker outage or WAF rule.  
- Cloudflare → WAF → Custom Rules: confirm no rule blocking `/version`.

**Backend 5xx / `/health` non‑200**
- `flyctl logs -a "$API_APP"` — identify stacktrace.  
- `flyctl scale count 1 -a "$API_APP"` — wake if parked.  
- If broken image, `flyctl releases -a "$API_APP"` → redeploy previous image.

**DNS / TLS**
- `dig +short backend.dhkalign.com` — must resolve CNAME to Fly.  
- Ensure **Full (Strict)** and **Proxied**; for cert issuance, set **DNS only** until Ready.

**Pro auth 401 via Edge**
- Verify `EDGE_SHIELD_TOKEN` match between Worker and Fly.  
- Confirm `x-api-key` provided on `/translate/pro`.

**Stripe webhook 400**
- Symptom: 400 at `/webhook/stripe` ("signature verification failed").
- Fix: set `STRIPE_WEBHOOK_SECRET` in Worker; confirm replay lock KV is present; verify the signing secret in Stripe dashboard.

**Edge cache always MISS**
- Symptom: `CF-Cache-Edge` never shows HIT.
- Fix: send identical method/path/body; avoid `?cache=no`; ensure cacheable status codes; confirm Worker isn't setting `Cache-Control: no-store`; warm with the GET example above and retry.

---

## 8) Releases / PR flow

```bash
# Create feature branch
git switch -c feat/<name>

# Commit work
git add -A && git commit -m "<msg>" && git push -u origin HEAD

# Open PR and auto-merge when checks pass
gh pr create --base main --head "$(git rev-parse --abbrev-ref HEAD)" --title "<title>" --body "<body>" || true
gh pr merge --squash --auto || true
```

*Required checks*: `Cloudflare Pages`, `smoke`. CodeQL may fail; it is non‑blocking.

---

## 9) Cost Discipline

- Keep Fly apps **parked** (scale 0) when idle.
- Prefer SQLite + edge cache; avoid eager OpenAI calls.
- Track egress if usage spikes.

---

## 10) Contacts

- **Ops**: info@dhkalign.com  
- **Security**: admin@dhkalign.com
