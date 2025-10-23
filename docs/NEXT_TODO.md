# DHK Align — Security Run Log (Post‑Incident Notes)

> One entry per incident. Append new entries to the **top**. Keep timestamps in **UTC**. Link artifacts when possible.

---

## Template (copy/paste for each new incident)

**Incident ID:** `YYYYMMDD-<short>`  
**Date (UTC):** `YYYY‑MM‑DD HH:MM` → `YYYY‑MM‑DD HH:MM`  
**Environment:** prod | dev  
**Severity:** Sev‑1 | Sev‑2 | Sev‑3  
**Status:** Open | Mitigated | Closed

### Summary
> 2–3 lines. What failed, who/what was impacted.

### Impact
- Affected routes / customers / latency / error rates.

### Detection
- How we noticed (monitor, alert, manual report).

### Timeline (UTC)
- `HH:MM` detected …  
- `HH:MM` first action …  
- `HH:MM` fix applied …  
- `HH:MM` verified …

### Root Cause
- Short causal chain; include config/code references.

### Fix
- What changed (config/secret/deploy/rollback). Include exact command(s) if relevant.

### Verification
- Paste the **smoke** you ran (edge/origin health, free GET+POST 200, pro with key 200/404 JSON, admin 401→200, Stripe bad sig → 400).  
- Include links to logs / screenshots where useful.

### Prevent / Follow‑ups
- [ ] Add/adjust alert (describe)  
- [ ] Add `/metrics` or log sampling (describe)  
- [ ] Document gap (file/section)  
- [ ] Test/Playbook update  
- [ ] Other …

### Artifacts
- Worker tail snippet: `<link or attached>`  
- Origin logs: `<link or attached>`  
- Stripe event IDs: `<evt_…>`  
- KV keys touched: `usage:<key>:<date>`, `session_to_key:<sid>`, `stripe_evt:<id>`

---

## 2025‑09‑22 — Example stub (remove once you log a real incident)
**Incident ID:** 20250922-shield-mismatch  
**Date (UTC):** 2025‑09‑22 22:10 → 22:26  
**Environment:** prod  
**Severity:** Sev‑2  
**Status:** Closed

### Summary
Origin returned 403 for `/translate/pro` after Worker deploy; users saw 5xx on Pro calls for ~10 minutes.

### Impact
- Pro route unavailable; free unaffected.

### Detection
- Manual curl + `wrangler tail --env production` showed 403 from origin.

### Timeline (UTC)
- 22:10 detected Worker 530/403  
- 22:14 identified shield mismatch  
- 22:19 set correct `EDGE_SHIELD_TOKEN` in Worker + redeployed  
- 22:26 verified Pro / free OK

### Root Cause
Worker prod secret `EDGE_SHIELD_TOKEN` did not match backend env after deploy.

### Fix
- Set `EDGE_SHIELD_TOKEN` in Worker prod: `wrangler secret put EDGE_SHIELD_TOKEN --env production`  
- Restarted backend with the same value.

### Verification
- `curl -is https://<WORKER_HOST>/edge/health` → 200  
- Free POST+GET → 200  
- Pro with key → 200/404 JSON  
- Admin guard → 401/200  
- Stripe bad sig → 400

### Prevent / Follow‑ups
- [x] Add prod cutover checklist item: verify shield on Worker + backend  
- [ ] Add origin `/metrics` (auth failures count)  
- [ ] Alert on 403 spike from origin

### Artifacts
- Tail excerpt attached  
- KV: no changes

# DHK Align - Next TODO (Oct 2025)

Single source of truth for what we do next. Keep tight, no fluff. Check off in place.

---

## Now - do in order

### 1) Frontend - Vite migration (no traffic switch)
Owner: Taj  
Branch: `feat/vite-migration`  
Status: [ ] Not started

- [ ] Add `frontend/vite.config.ts` and minimal `frontend/index.html` (keep CRA scripts in package.json).
- [ ] Confirm dev runs: `npm run dev` (Vite) and existing CRA still builds.
- [ ] Ensure SPA fallback stays: Pages `_redirects` or framework setting unchanged for now.
- [ ] Do not change Pages output yet (still `frontend/build`).
- [ ] Open PR and merge. No user-facing change.

**Verify**
```bash
# local
npm --prefix frontend run build   # CRA still builds
# vite check
node -e "process.exit(require('fs').existsSync('frontend/vite.config.ts')?0:1)"
```

---

### 2) Data ingestion v1 - schema v2, seed, validator, loader, CI
Owner: Taj  
Branch: `feat/ingest-v1`  
Status: [ ] Not started

- [ ] `data/packs/README.md` - confirm schema v2 (id, src_lang, tgt_lang, src_text, tgt_text, source_url, license, created_at RFC3339 Z, quality 0..1).
- [ ] Add seed pack: `data/packs/banglish_seed@0.1.0.jsonl` (at least 10 rows, quality >= 0.7).
- [ ] Validator: `scripts/validate_jsonl.py` (jsonschema) and CI: `.github/workflows/validate-pack.yml`.
- [ ] Loader: `backend/scripts/import_jsonl_to_sqlite.py` - import seed into `backend/data/translations.db`.
- [ ] Backend points to DB-first free path. Pro fallback remains optional.
- [ ] Smoke: free GET and POST return a seed example.
- [ ] Docs: update a short note in `EXECUTION_DELIVERABLES.md` under Data.

**Verify**
```bash
python3 scripts/validate_jsonl.py data/packs/banglish_seed@0.1.0.jsonl
python3 backend/scripts/import_jsonl_to_sqlite.py data/packs/banglish_seed@0.1.0.jsonl
curl -fsS 'https://edge.dhkalign.com/api/translate?q=Rickshaw%20pabo%20na' | jq
curl -fsS -X POST 'https://edge.dhkalign.com/translate' -H 'content-type: application/json' \
  -d '{"q":"Rickshaw pabo na"}' | jq
```

---

## After that - short list

- [ ] Stripe UI on Pages - CSP allow Stripe, host Apple Pay association file.
- [ ] Worker flag to canary Go sidecar 1 to 5 percent once parity exists.
- [ ] Metrics polish - ensure `/metrics` has DB hit and fallback counters.
- [ ] Secrets audit - confirm `EDGE_SHIELD_TOKEN`, `ADMIN_KEY`, Stripe keys in Worker; OpenAI keys only if fallback on.

---

## Done - leave a dated line when you finish an item
- 2025-..-.. Vite config merged, no traffic switch.
- 2025-..-.. Ingest v1 imported, smoke passing.

---

## Appendix - Security run log template (kept for convenience)

> One entry per incident. Append new entries to the top. Keep timestamps in UTC. Link artifacts when possible.

**Incident ID:** `YYYYMMDD-<short>`  
**Date (UTC):** `YYYY-MM-DD HH:MM` -> `YYYY-MM-DD HH:MM`  
**Environment:** prod | dev  
**Severity:** Sev-1 | Sev-2 | Sev-3  
**Status:** Open | Mitigated | Closed

### Summary
2 to 3 lines. What failed, who or what was impacted.

### Impact
- Affected routes / customers / latency / error rates.

### Detection
- How we noticed (monitor, alert, manual report).

### Timeline (UTC)
- `HH:MM` detected ...  
- `HH:MM` first action ...  
- `HH:MM` fix applied ...  
- `HH:MM` verified ...

### Root Cause
- Short causal chain; include config or code references.

### Fix
- What changed (config, secret, deploy, rollback). Include exact commands if relevant.

### Verification
- Use the standard smoke in `SECURITY_RUN_LOG.md`.

### Prevent / Follow-ups
- [ ] Add or adjust alert (describe)  
- [ ] Add `/metrics` or log sampling (describe)  
- [ ] Document gap (file and section)  
- [ ] Test or playbook update  
- [ ] Other ...

### Artifacts
- Worker tail snippet: `<link or attached>`  
- Origin logs: `<link or attached>`  
- Stripe event IDs: `<evt_...>`  
- KV keys touched: `usage:<key>:<date>`, `session_to_key:<sid>`, `stripe_evt:<id>`