import json, sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB   = ROOT / "data" / "translations.db"
OUT  = ROOT.parent / "frontend" / "src" / "data" / "dhk_align_client.json"

OUT.parent.mkdir(parents=True, exist_ok=True)

conn = sqlite3.connect(DB)
cur  = conn.cursor()
cur.execute("""
  SELECT banglish, english
  FROM translations
  WHERE COALESCE(safety_level,1) <= 1
""")
rows = cur.fetchall()
conn.close()

cache = {b: e for b, e in rows}
with open(OUT, "w", encoding="utf-8") as f:
  json.dump({"v":"1.0","t":cache}, f, ensure_ascii=False, indent=2)

print(f"Wrote {OUT} with {len(cache)} entries (safety<=1).")
