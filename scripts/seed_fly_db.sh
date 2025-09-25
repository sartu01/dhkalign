#!/usr/bin/env bash
set -euo pipefail

APP="${APP:-dhkalign-backend}"
DB_LOCAL="${DB_LOCAL:-$HOME/Dev/dhkalign/backend/data/translations.db}"
DB_REMOTE="/app/backend/data/translations.db"

# sanity
command -v flyctl >/dev/null || { echo "flyctl not found"; exit 1; }
[ -f "$DB_LOCAL" ] || { echo "Local DB not found: $DB_LOCAL"; exit 1; }

echo "== Seeding $DB_LOCAL -> fly app: $APP =="
# ensure remote dir
flyctl ssh console -a "$APP" -C "mkdir -p /app/backend/data"

# upload raw (no base64 quirks)
flyctl ssh console -a "$APP" -C "cat > '$DB_REMOTE'" < "$DB_LOCAL"

# verify
echo "== Verifying row count =="
flyctl ssh console -a "$APP" -C \
"python - <<'PY'
import sqlite3
db='$DB_REMOTE'
con=sqlite3.connect(db)
cur=con.cursor()
try:
    cur.execute('SELECT COUNT(*) FROM translations')
    print(cur.fetchone()[0])
except Exception as e:
    print('ERROR:', e)
finally:
    con.close()
PY"
echo "== Done =="
