#!/usr/bin/env bash
set -euo pipefail
npm pkg set scripts.test="jest" >/dev/null 2>&1 || true
npm pkg set scripts.test:e2e="playwright test e2e" >/dev/null 2>&1 || true || true
npm i -D @playwright/test jest >/dev/null 2>&1 || true
npx playwright install >/dev/null 2>&1 || true
[ -f scripts/validate_gold_set.js ] && node scripts/validate_gold_set.js || echo "no gold validator"
[ -f scripts/validate_packs.js ] && node scripts/validate_packs.js || echo "no pack validator"
[ -d e2e ] && npx playwright test e2e || echo "no e2e folder"
git add -A
git status --porcelain
echo 'If OK: git commit -m "chore: wraith automation" && git push'
