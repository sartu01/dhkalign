from __future__ import annotations
import os
import json
import time
from typing import Optional

import httpx

# Env knobs
OPENAI_API_KEY  = (os.getenv("OPENAI_API_KEY") or "").strip()
OPENAI_BASE_URL = (os.getenv("OPENAI_BASE_URL") or "https://api.openai.com").strip()
OPENAI_ORG      = (os.getenv("OPENAI_ORG") or "").strip()  # optional
GPT_MODEL       = (os.getenv("GPT_MODEL") or "gpt-4o-mini").strip() or "gpt-4o-mini"
# clamp tokens to a safe small range (protect cost/latency)
try:
    _tok = int(os.getenv("GPT_MAX_TOKENS") or 128)
except Exception:
    _tok = 128
GPT_MAX_TOKENS  = max(1, min(_tok, 512))
try:
    _ms = int(os.getenv("GPT_TIMEOUT_MS") or 2000)
except Exception:
    _ms = 2000
GPT_TIMEOUT_MS  = max(250, min(_ms, 10000))  # 0.25s .. 10s
try:
    _rt = int(os.getenv("GPT_RETRIES") or 2)
except Exception:
    _rt = 2
GPT_RETRIES     = max(0, min(_rt, 5))        # 0..5 retries
DEBUG_FALLBACK  = (os.getenv("DEBUG_FALLBACK") or "").strip().lower() in {"1","true","on","yes"}

TIMEOUT = httpx.Timeout(GPT_TIMEOUT_MS / 1000.0)
CHAT_URL = f"{OPENAI_BASE_URL.rstrip('/')}/v1/chat/completions"

SYSTEM_PROMPT = (
    "You are a precise translator. Convert Banglish (romanized Bengali) to the target language. "
    "Prefer concise everyday wording. Return ONLY the translated text without quotes."
)

# legacy no-op kept for compatibility

def translate(text: str, src_lang: str, tgt_lang: str) -> None:
    return None


def _clip_text(s: str, max_chars: int = 4000) -> str:
    if not s:
        return ""
    s = str(s)
    s = s.strip()
    return s[:max_chars] if len(s) > max_chars else s


def _client() -> httpx.Client:
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if OPENAI_ORG:
        headers["OpenAI-Organization"] = OPENAI_ORG
    return httpx.Client(timeout=TIMEOUT, headers=headers)


def _post_with_retries(client: httpx.Client, url: str, payload: dict) -> Optional[httpx.Response]:
    delay = 0.2
    for attempt in range(GPT_RETRIES + 1):
        try:
            resp = client.post(url, content=json.dumps(payload))
            if resp.status_code == 200:
                return resp
            # retry on transient issues
            if resp.status_code in (429, 500, 502, 503, 504) and attempt < GPT_RETRIES:
                if DEBUG_FALLBACK:
                    print(f"[gpt-fallback] retry {attempt+1} status={resp.status_code}")
                time.sleep(delay)
                delay = min(delay * 2, 2.0)
                continue
            if DEBUG_FALLBACK:
                try:
                    body = resp.text[:300]
                except Exception:
                    body = "<unreadable>"
                print(f"[gpt-fallback] fail status={resp.status_code} body={body}")
            return None
        except Exception as e:
            if attempt < GPT_RETRIES:
                if DEBUG_FALLBACK:
                    print(f"[gpt-fallback] exception retry {attempt+1}: {e!r}")
                time.sleep(delay)
                delay = min(delay * 2, 2.0)
                continue
            if DEBUG_FALLBACK:
                print(f"[gpt-fallback] exception final: {e!r}")
            return None
    return None


def gpt_translate(text: str, src_lang: str = "bn-rom", tgt_lang: str = "en") -> Optional[dict]:
    """Synchronous GPT call. Returns {"tgt": str, "model": str} or None on failure.

    Kept sync to avoid changing callers. Tight timeout; small tokens; simple backoff on 429/5xx.
    """
    if not OPENAI_API_KEY:
        return None

    text = _clip_text(text)
    if not text:
        return None

    payload = {
        "model": GPT_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": f"Translate from {src_lang or 'bn-rom'} to {tgt_lang or 'en'}: {text}"},
        ],
        "temperature": 0.2,
        "max_tokens": GPT_MAX_TOKENS,
    }

    try:
        with _client() as client:
            resp = _post_with_retries(client, CHAT_URL, payload)
        if not resp:
            return None
        data = resp.json()
        # pick content defensively
        tgt = None
        try:
            tgt = (data.get("choices") or [{}])[0].get("message", {}).get("content", "").strip()
        except Exception:
            tgt = None
        if not tgt:
            return None
        return {"tgt": tgt, "model": data.get("model", GPT_MODEL)}
    except Exception as e:
        if DEBUG_FALLBACK:
            print(f"[gpt-fallback] outer exception: {e!r}")
        return None