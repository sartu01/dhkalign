from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path
import sqlite3

DB = Path(__file__).parent / "data" / "translations.db"
router = APIRouter()

class TranslateProReq(BaseModel):
    text: str
    pack: str | None = None

def connect():
    conn = sqlite3.connect(DB, timeout=5.0, isolation_level=None)
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

@router.post("/translate/pro")
def translate_pro(req: TranslateProReq):
    text = (req.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text required")
    if not DB.exists():
        raise HTTPException(status_code=500, detail="DB missing")

    conn = connect(); cur = conn.cursor()
    if req.pack:
        cur.execute("""
          SELECT english FROM translations
          WHERE (banglish=? OR lower(banglish)=lower(?))
            AND COALESCE(safety_level,1)>=2
            AND lower(COALESCE(pack,''))=lower(?)
          ORDER BY ROWID DESC LIMIT 1
        """, (text, text, req.pack))
    else:
        cur.execute("""
          SELECT english FROM translations
          WHERE (banglish=? OR lower(banglish)=lower(?))
            AND COALESCE(safety_level,1)>=2
          ORDER BY ROWID DESC LIMIT 1
        """, (text, text))
    row = cur.fetchone(); conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Pro translation not found")
    return {"src": req.text, "dst": row[0], "tier": "pro", "pack": req.pack}
