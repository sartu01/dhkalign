# DHK Align — Security Run Log (Post-Incident Notes)
> One entry per incident. Append new entries to the **top**. Keep timestamps in **UTC**. Link artifacts when possible.

## Template (copy/paste for each new incident)
**Incident ID:** `YYYYMMDD-<short>`  
**Date (UTC):** `YYYY-MM-DD HH:MM` → `YYYY-MM-DD HH:MM`  
**Environment:** prod | dev  
**Severity:** Sev-1 | Sev-2 | Sev-3  
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
- Paste the smoke you ran (edge/origin health, free GET+POST 200, pro 200/404 JSON, admin 401→200, Stripe bad sig → 400).
- Include links to logs / screenshots.

### Prevent / Follow-ups
- [ ] Add/adjust alert (describe)
- [ ] Add `/metrics` or log sampling (describe)
- [ ] Document gap (file/section)
- [ ] Test/Playbook update
- [ ] Other …

### Artifacts
- Worker tail snippet: <link or attached>
- Origin logs: <link or attached>
- Stripe event IDs: <evt_…>
- KV keys touched: usage:<key>:<date>, session_to_key:<sid>, stripe_evt:<id>
