#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$HOME/Dev/dhkalign"
cd "$ROOT"

echo "▶ repo sanity"
test -f backend/main.py || { echo "backend/main.py missing"; exit 1; }
test -f infra/edge/wrangler.toml || { echo "infra/edge/wrangler.toml missing"; exit 1; }

echo "▶ clean backend junk"
rm -rf backend/node_modules backend/package.json backend/package-lock.json 2>/dev/null || true

echo "▶ remove runtime.txt drift if present"
[ -f runtime.txt ] && git rm -f runtime.txt || true

echo "▶ venv + deps"
python3 -m venv backend/.venv
source backend/.venv/bin/activate
python -V
pip install -U pip wheel setuptools
if [ -f backend/requirements.txt ]; then
  pip install -r backend/requirements.txt
elif [ -f requirements.txt ]; then
  pip install -r requirements.txt
else
  echo "no requirements.txt found"; exit 1
fi

# ensure pandas if app imports it
python - <<'PY' || pip install pandas
import importlib, sys
m = importlib.util.find_spec("pandas")
print("pandas:", "found" if m else "missing")
if m is None: sys.exit(1)
PY

echo "▶ canonical DB = backend/data/translations.db"
mkdir -p backend/data
DB_CANON="backend/data/translations.db"
if [ ! -f "$DB_CANON" ]; then
  if [ -f private/translations.db ]; then
    cp -f private/translations.db "$DB_CANON"
  elif [ -f backend/dhk_align.db ]; then
    cp -f backend/dhk_align.db "$DB_CANON"
  fi
fi
[ -f "$DB_CANON" ] || { echo "ERR: no DB found (private/translations.db or backend/dhk_align.db)"; exit 1; }

echo "▶ normalize DB fields + unique index (safe re-run)"
sqlite3 "$DB_CANON" 'PRAGMA journal_mode=WAL;'
HAS_COL=$(sqlite3 "$DB_CANON" "PRAGMA table_info(translations);" | awk -F'|' '$2=="roman_bn_norm"{print $2}')
if [ -z "$HAS_COL" ]; then
  sqlite3 "$DB_CANON" 'ALTER TABLE translations ADD COLUMN roman_bn_norm TEXT;'
fi
sqlite3 "$DB_CANON" '
  UPDATE translations
     SET roman_bn_norm = LOWER(TRIM(banglish))
   WHERE COALESCE(roman_bn_norm,"")="";
  CREATE UNIQUE INDEX IF NOT EXISTS uq_phrase_on_norm
    ON translations(src_lang, roman_bn_norm, tgt_lang, pack);
  VACUUM;
'
echo "▶ counts by pack and safety"
sqlite3 "$DB_CANON" 'SELECT pack, safety_level, COUNT(*) FROM translations GROUP BY 1,2 ORDER BY 1,2;'
echo "✔ setup done"
