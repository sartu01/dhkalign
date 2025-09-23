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
