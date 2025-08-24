from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3
from pathlib import Path

DB = Path(__file__).parent / "data" / "translations.db"
app = FastAPI(title="DHK Align API (SQLite)", version="1.0")
from backend.pro_routes import router as pro_router
app.include_router(pro_router)
from backend.security_middleware import SecurityMiddleware
app.add_middleware(SecurityMiddleware)

class TranslateReq(BaseModel):
    text: str
    src_lang: str = "banglish"
    dst_lang: str = "english"

def query_safe(text, src, dst):
    if not DB.exists(): return None
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("""
        SELECT english FROM translations
        WHERE (banglish = ? OR lower(banglish) = lower(?))
          AND COALESCE(safety_level, 1) <= 1
        ORDER BY ROWID DESC LIMIT 1
    """, (text, text))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None

@app.get("/health")
def health():
    cnt = 0
    if DB.exists():
        conn = sqlite3.connect(DB); cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM translations WHERE COALESCE(safety_level,1) <= 1")
        cnt = cur.fetchone()[0] or 0
        conn.close()
    return {"ok": DB.exists(), "db": str(DB), "safe_rows": cnt}

@app.post("/translate")
def translate(req: TranslateReq):
    hit = query_safe(req.text.strip(), req.src_lang.lower(), req.dst_lang.lower())
    if not hit:
        raise HTTPException(status_code=404, detail="Translation not available (safe tier)")
    return {"src": req.text, "dst": hit}
