from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import sqlite3

DB = Path(__file__).parent / "data" / "translations.db"
router = APIRouter()

class TranslateProReq(BaseModel):
    text: str
    pack: Optional[str] = None
    src_lang: Optional[str] = None
    tgt_lang: Optional[str] = None

class TranslateReq(BaseModel):
    text: str
    src_lang: Optional[str] = None
    tgt_lang: Optional[str] = None


def connect():
    conn = sqlite3.connect(DB, timeout=5.0, isolation_level=None)
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


@router.post("/translate/pro")
def translate_pro(req: TranslateProReq):
    text = (req.text or "").strip()
    if not text:
        return JSONResponse({"ok": False, "error": "text_required"}, status_code=400)
    if not DB.exists():
        return JSONResponse({"ok": False, "error": "db_missing"}, status_code=500)

    conn = connect(); cur = conn.cursor()
    try:
        if req.pack:
            cur.execute(
                """
                SELECT banglish, english, src_lang, tgt_lang, pack
                FROM translations
                WHERE COALESCE(safety_level,1) >= 2
                  AND (
                    lower(banglish) = lower(?)
                    OR (
                      (SELECT name FROM pragma_table_info('translations') WHERE name='roman_bn_norm' LIMIT 1) IS NOT NULL
                      AND lower(COALESCE(roman_bn_norm,'')) = lower(?)
                    )
                  )
                  AND lower(COALESCE(pack,'')) = lower(?)
                ORDER BY ROWID DESC LIMIT 1
                """,
                (text, text, req.pack)
            )
        else:
            cur.execute(
                """
                SELECT banglish, english, src_lang, tgt_lang, pack
                FROM translations
                WHERE COALESCE(safety_level,1) >= 2
                  AND (
                    lower(banglish) = lower(?)
                    OR (
                      (SELECT name FROM pragma_table_info('translations') WHERE name='roman_bn_norm' LIMIT 1) IS NOT NULL
                      AND lower(COALESCE(roman_bn_norm,'')) = lower(?)
                    )
                  )
                ORDER BY ROWID DESC LIMIT 1
                """,
                (text, text)
            )
        row = cur.fetchone()
    finally:
        conn.close()

    if not row:
        return JSONResponse({"ok": False, "error": "not_found"}, status_code=404)

    data = {
        "src": row["banglish"] or req.text,
        "tgt": row["english"],
        "src_lang": row["src_lang"] or (req.src_lang or "bn-rom"),
        "tgt_lang": row["tgt_lang"] or (req.tgt_lang or "en"),
        "tier": "pro",
        "pack": row["pack"] or req.pack,
        "source": "db",
    }
    return JSONResponse({"ok": True, "data": data})


@router.post("/translate")
def translate(req: TranslateReq):
    text = (req.text or "").strip()
    if not text:
        return JSONResponse({"ok": False, "error": "text_required"}, status_code=400)
    if not DB.exists():
        return JSONResponse({"ok": False, "error": "db_missing"}, status_code=500)

    conn = connect(); cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT banglish, english, src_lang, tgt_lang, pack
            FROM translations
            WHERE COALESCE(safety_level,1) <= 1
              AND (
                lower(banglish) = lower(?)
                OR (
                  (SELECT name FROM pragma_table_info('translations') WHERE name='roman_bn_norm' LIMIT 1) IS NOT NULL
                  AND lower(COALESCE(roman_bn_norm,'')) = lower(?)
                )
              )
            ORDER BY ROWID DESC LIMIT 1
            """,
            (text, text)
        )
        row = cur.fetchone()
    finally:
        conn.close()

    if not row:
        return JSONResponse({"ok": False, "error": "not_found"}, status_code=404)

    data = {
        "src": row["banglish"] or req.text,
        "tgt": row["english"],
        "src_lang": row["src_lang"] or (req.src_lang or "bn-rom"),
        "tgt_lang": row["tgt_lang"] or (req.tgt_lang or "en"),
        "tier": "free",
        "pack": row["pack"],
        "source": "db",
    }
    return JSONResponse({"ok": True, "data": data})
