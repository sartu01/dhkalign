import sys, json, sqlite3
from pathlib import Path

if len(sys.argv) < 2:
    print("Usage: import_clean_jsonl.py <file.CLEAN.jsonl>")
    sys.exit(1)

path = Path(sys.argv[1])
DB = Path(__file__).resolve().parents[1] / "data" / "translations.db"
conn = sqlite3.connect(DB)
cur = conn.cursor()

inserted = updated = skipped = 0
with open(path, "r", encoding="utf-8") as f:
    for line in f:
        line=line.strip()
        if not line: continue
        try:
            j = json.loads(line)
            b = j["banglish"].strip()
            e = j["english"].strip()
            pack = str(j.get("pack","misc"))
            safety = int(j.get("safety_level", 1))
        except Exception:
            skipped += 1
            continue

        # try update first (case-insensitive on banglish)
        cur.execute("""UPDATE translations
                          SET english=?, safety_level=?, pack=?
                        WHERE lower(banglish)=lower(?)""",
                    (e, safety, pack, b))
        if cur.rowcount == 0:
            cur.execute("""INSERT INTO translations (banglish, english, safety_level, pack)
                           VALUES (?, ?, ?, ?)""", (b, e, safety, pack))
            inserted += 1
        else:
            updated += 1

conn.commit(); conn.close()
print(f"{path.name}: inserted={inserted}, updated={updated}, skipped={skipped}")
