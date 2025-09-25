
from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import os
import sqlite3
from pathlib import Path
import inspect

ENABLE_GPT = os.getenv("ENABLE_GPT_FALLBACK", "0").lower() in ("1", "true", "yes", "on")
GPT_SRC_DEFAULT = os.getenv("GPT_SRC_LANG_DEFAULT", "bn-rom")
GPT_TGT_DEFAULT = os.getenv("GPT_TGT_LANG_DEFAULT", "en")

# SQLite DB path (works both locally and in container)
DB_PATH = os.getenv("DB_PATH") or str((Path(__file__).parent / "data" / "translations.db").resolve())

try:
    from backend.services.model_adapter import gpt_translate
except ImportError:
    gpt_translate = None
try:
    from backend.services.model_adapter import translate_fallback
except ImportError:
    translate_fallback = None

def _fetch_free_translation(text: str, src_lang: str | None = None, tgt_lang: str | None = None):
    if not text:
        return None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        # Try exact match on normalized and raw banglish, but only free tier (safety_level <= 1)
        cur.execute(
            """
            SELECT banglish, english, src_lang, tgt_lang, pack
            FROM translations
            WHERE COALESCE(safety_level,1) <= 1
              AND (
                 lower(banglish) = lower(?)
                 OR (CASE WHEN (SELECT name FROM pragma_table_info('translations') WHERE name='roman_bn_norm' LIMIT 1) IS NOT NULL
                          THEN lower(COALESCE(roman_bn_norm, '')) = lower(?)
                          ELSE 0 END)
              )
            LIMIT 1
            """,
            (text, text),
        )
        row = cur.fetchone()
        return dict(row) if row else None
    except Exception:
        return None
    finally:
        try:
            conn.close()
        except Exception:
            pass

def _fetch_pro_translation(text: str, src_lang: str | None = None, tgt_lang: str | None = None):
    if not text:
        return None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        # Try exact/normalized match for pro tier (safety_level >= 2)
        cur.execute(
            """
            SELECT banglish, english, src_lang, tgt_lang, pack
            FROM translations
            WHERE COALESCE(safety_level,1) >= 2
              AND (
                 lower(banglish) = lower(?)
                 OR (CASE WHEN (SELECT name FROM pragma_table_info('translations') WHERE name='roman_bn_norm' LIMIT 1) IS NOT NULL
                          THEN lower(COALESCE(roman_bn_norm, '')) = lower(?)
                          ELSE 0 END)
              )
            LIMIT 1
            """,
            (text, text),
        )
        row = cur.fetchone()
        return dict(row) if row else None
    except Exception:
        return None
    finally:
        try:
            conn.close()
        except Exception:
            pass

def _insert_pro_auto_row(text: str, translated: str, src_lang: str, tgt_lang: str):
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT OR IGNORE INTO translations
              (id, banglish, english, src_lang, tgt_lang, pack, safety_level, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (f"gpt_{abs(hash(text))}", text, translated, src_lang, tgt_lang, "gpt_fallback", 2, "gpt"),
        )
        conn.commit()
    except Exception:
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass

router = APIRouter()

# Create FastAPI app and mount this router so uvicorn can import backend.app_sqlite:app

app = FastAPI()

# Convert unexpected errors on translate endpoints into safe 404 JSON
@app.exception_handler(Exception)
async def _unhandled_any(request, exc):
    p = request.url.path
    if p.endswith('/translate') or p.endswith('/translate/pro'):
        return JSONResponse({"ok": False, "error": "not_found"}, status_code=404)
    return JSONResponse({"ok": False, "error": "internal_error"}, status_code=500)

@app.get("/health")
async def health():
    return {"ok": True}

# (router mounted below after route definitions)

#
# Free translate endpoints (GET/POST). Minimal implementation that avoids 500s.
@router.get("/translate")
async def translate_free_get(q: str | None = None):
    if not q:
        return JSONResponse({"ok": False, "error": "missing_query"}, status_code=400)
    hit = _fetch_free_translation(q)
    if not hit:
        return JSONResponse({"ok": False, "error": "not_found"}, status_code=404)
    return JSONResponse({"ok": True, "data": {
        "src": hit.get("banglish") or q,
        "tgt": hit.get("english"),
        "src_lang": hit.get("src_lang") or "bn-rom",
        "tgt_lang": hit.get("tgt_lang") or "en",
        "pack": hit.get("pack") or "everyday",
        "source": "db"
    }})

@router.post("/translate")
async def translate_free_post(request: Request, text: str | None = None, src_lang: str | None = None, tgt_lang: str | None = None):
    if not text:
        try:
            body = await request.json()
            if isinstance(body, dict):
                text = body.get("text") or body.get("q")
                src_lang = body.get("src_lang") or body.get("src") or src_lang
                tgt_lang = body.get("tgt_lang") or body.get("tgt") or tgt_lang
        except Exception:
            pass
    if not text:
        return JSONResponse({"ok": False, "error": "invalid_json"}, status_code=400)
    hit = _fetch_free_translation(text, src_lang, tgt_lang)
    if not hit:
        return JSONResponse({"ok": False, "error": "not_found"}, status_code=404)
    return JSONResponse({"ok": True, "data": {
        "src": hit.get("banglish") or text,
        "tgt": hit.get("english"),
        "src_lang": hit.get("src_lang") or (src_lang or "bn-rom"),
        "tgt_lang": hit.get("tgt_lang") or (tgt_lang or "en"),
        "pack": hit.get("pack") or "everyday",
        "source": "db"
    }})


@router.post("/translate/pro")
async def translate_pro(request: Request, text: str = None, src_lang: str = None, tgt_lang: str = None):
    # Parse input from args or JSON body
    _text = text
    _src = src_lang
    _tgt = tgt_lang
    if not _text:
        try:
            body = await request.json()
            if isinstance(body, dict):
                _text = body.get("text") or body.get("q")
                _src = body.get("src_lang") or body.get("src") or _src
                _tgt = body.get("tgt_lang") or body.get("tgt") or _tgt
        except Exception:
            pass

    if not _text:
        return JSONResponse({"ok": False, "error": "invalid_json"}, status_code=400)

    # Try DB lookup first
    hit = _fetch_pro_translation(_text, _src, _tgt)
    if hit:
        return JSONResponse({"ok": True, "data": {
            "src": hit.get("banglish") or _text,
            "tgt": hit.get("english"),
            "src_lang": hit.get("src_lang") or (_src or "bn-rom"),
            "tgt_lang": hit.get("tgt_lang") or (_tgt or "en"),
            "pack": hit.get("pack") or "everyday",
            "source": "db"
        }})

    if ENABLE_GPT:
        # Use gpt_translate if available (returns dict), else translate_fallback (may be str or awaitable)
        translator = gpt_translate or translate_fallback
        if not translator:
            return JSONResponse({"ok": False, "error": "not_found"}, status_code=404)

        english = None
        try:
            if inspect.iscoroutinefunction(translator):
                out = await translator(_text, _src or GPT_SRC_DEFAULT, _tgt or GPT_TGT_DEFAULT)
            else:
                out = translator(_text, _src or GPT_SRC_DEFAULT, _tgt or GPT_TGT_DEFAULT)
            if isinstance(out, dict):
                english = (out.get("tgt") or "").strip() or None
            else:
                english = (out or "").strip() or None
        except Exception:
            english = None

        if english:
            _insert_pro_auto_row(_text, english, _src or GPT_SRC_DEFAULT, _tgt or GPT_TGT_DEFAULT)
            return JSONResponse({"ok": True, "data": {
                "src": _text,
                "tgt": english,
                "src_lang": _src or GPT_SRC_DEFAULT,
                "tgt_lang": _tgt or GPT_TGT_DEFAULT,
                "pack": "gpt_fallback",
                "source": "gpt"
            }})

    return JSONResponse({"ok": False, "error": "not_found"}, status_code=404)

# Mount local routes (must run after route definitions)
app.include_router(router)

# Mount pro routes explicitly (ensures /translate/pro is registered if defined externally)
try:
    from backend.pro_routes import router as pro_router
    app.include_router(pro_router)
except Exception as e:
    print("[app_sqlite] WARN: failed to mount pro_routes:", repr(e))

# (rest of the file unchanged)

# ---
