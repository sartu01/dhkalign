

# DHK Align - CI (GitHub Actions)

Single source of truth for our CI. Keep it surgical and fast.

## Required checks on main
- Cloudflare Pages
- smoke

These two checks are required under the branch protection rule for `main`. CodeQL is optional and not a blocker.

## Workflows in this repo
- `.github/workflows/smoke.yml`  
  Purpose: external black-box smoke against production. Tolerant and fast. Non-blocking subchecks for Go sidecar.
- `.github/workflows/validate-pack.yml`  
  Purpose: validate JSONL packs against schema v2 during data work. Only runs when files under `data/packs/` or `scripts/validate_jsonl.py` change.

## What the smoke workflow validates
1. DNS and redirects
   - `https://dhkalign.com` returns 200
   - `https://www.dhkalign.com/...` returns 301 to apex
2. Edge and origin health
   - `https://edge.dhkalign.com/version` returns JSON containing a `sha` or `commit`
   - `https://backend.dhkalign.com/health` returns `{ ok: true, ... }`
3. Free translate through Edge
   - GET `https://edge.dhkalign.com/api/translate?q=Rickshaw%20pabo%20na` returns 200 JSON
   - POST `https://edge.dhkalign.com/translate` with `{"q":"Rickshaw pabo na"}` returns 200 JSON
4. Go sidecar health (non-blocking)
   - If a Fly app is detected from `backend-go/fly.toml`, hit `/go/health`. This does not fail the job if the sidecar is parked.

## Typical smoke YAML snippet
This is illustrative. The actual workflow in the repo may be more compact, but must keep these assertions.
```yaml
name: smoke
on:
  workflow_dispatch: {}
  pull_request:
    branches: [ main ]
  push:
    branches: [ main ]
jobs:
  smoke:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - name: DNS apex 200
        run: |
          curl -sS -I https://dhkalign.com | head -n1 | grep -E '200|HTTP/2'
      - name: www 301 to apex
        run: |
          curl -sS -I https://www.dhkalign.com/test?q=1 | grep -E '^HTTP/.* 301' 
      - name: Edge /version
        run: |
          curl -sS https://edge.dhkalign.com/version | jq -e '.sha // .commit // empty' >/dev/null
      - name: Origin /health
        run: |
          curl -sS https://backend.dhkalign.com/health | jq -e '.ok == true'
      - name: Free GET via Edge
        run: |
          curl -sS 'https://edge.dhkalign.com/api/translate?q=Rickshaw%20pabo%20na' | jq -e '.translation // .tgt_text // empty' >/dev/null
      - name: Free POST via Edge
        run: |
          curl -sS -X POST 'https://edge.dhkalign.com/translate' \
            -H 'content-type: application/json' \
            -d '{"q":"Rickshaw pabo na"}' | jq -e '.translation // .tgt_text // empty' >/dev/null
      - name: Go sidecar health (non-blocking)
        continue-on-error: true
        run: |
          set -eu
          if [ -f backend-go/fly.toml ]; then
            curl -sS https://$(awk -F'\"' '/^app = /{print $2}' backend-go/fly.toml).fly.dev/go/health | jq -e '.ok == true'
          else
            echo "no backend-go/fly.toml, skipping"
          fi
```

## Pack validation workflow
The pack validator uses `jsonschema` to enforce schema v2:
- Required fields: `id`, `src_lang`, `tgt_lang`, `src_text`, `tgt_text`, `source_url`, `license`, `created_at` (RFC3339 Z), `quality` (0..1)
- Enums: `src_lang` in `{"bn-rom","en"}`, `tgt_lang` in `{"en","bn-rom"}`
- Disallow unknown keys

Example run locally:
```bash
python3 scripts/validate_jsonl.py data/packs/banglish_seed@0.1.0.jsonl
```

## Branch protection shape
- Base branch: `main`
- Required status checks: `Cloudflare Pages`, `smoke`
- Dismiss stale reviews: off
- Require PR approvals: 0 for speed mode

## How to run smoke manually
```bash
# last run on current branch
gh run list --workflow smoke -L 1
# trigger against main
gh workflow run smoke -r main
# watch latest execution
gh run watch --exit-status
```

## Adding a new smoke check
- Keep each step under 3 seconds. Use `jq -e` with a permissive selector.
- Never depend on private hosts or secrets. All hits are against public endpoints.
- For new public routes at Edge, add both GET and POST samples if applicable.
- If a check is flaky, mark it `continue-on-error: true` and add a note at the end of this doc explaining why.

## Common failures and fixes
- Edge GET fails on free route  
  Fix: ensure the canonical path is `/api/translate?q=...`. Legacy `/translate?q=...` should not be used in CI.
- Origin 403 in logs during smoke  
  Fix: `EDGE_SHIELD_TOKEN` mismatch. Set the same value in Worker and Fly and redeploy both.
- Go sidecar step fails the job  
  Fix: it should be non-blocking. Ensure `continue-on-error: true` is set and that step comes after critical checks.
- Redirect step fails  
  Fix: ensure `www` is proxied in Cloudflare DNS and the Pages redirect rule is in place.

## References
- `docs/EXECUTION_DELIVERABLES.md` - One-minute verification
- `docs/API.md` - Canonical API
- `docs/OPS.md` - Ops and runbooks
- `docs/SECURITY_RUNBOOK.md` - Incident handling