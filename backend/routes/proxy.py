import os
import asyncio
import httpx
from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from pydantic import BaseModel
from backend.utils import logger

router = APIRouter()
EDGE_DEFAULT = "https://edge.dhkalign.com"

MAX_Q_LEN = 256
RETRY_ATTEMPTS = 2  # total requests = RETRY_ATTEMPTS + 1
RETRY_STATUSES = {502, 503, 504}
HTTP_TIMEOUT = httpx.Timeout(10.0, connect=3.0)

class Body(BaseModel):
  q: str

@router.post("/api/pro-translate")
async def pro_translate(
    b: Body,
    x_turnstile: Optional[str] = Header(default=None, convert_underscores=False),
):
    q = (b.q or "").strip()
    q = q[:MAX_Q_LEN]
    if not q:
        raise HTTPException(status_code=400, detail="empty_query")

    # Read current env each call so key rotations take effect without restart
    EDGE = (os.getenv("EDGE_BASE_URL", EDGE_DEFAULT) or "").strip() or EDGE_DEFAULT
    if not EDGE.startswith("http://") and not EDGE.startswith("https://"):
        logger.warning("Invalid EDGE_BASE_URL %r; falling back to default", EDGE)
        EDGE = EDGE_DEFAULT
    base = EDGE[:-1] if EDGE.endswith('/') else EDGE
    url = f"{base}/translate/pro"

    EDGE_KEY = os.getenv("EDGE_API_KEY", "")
    if not EDGE_KEY:
        raise HTTPException(status_code=500, detail="edge_key_missing")

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": EDGE_KEY,
    }
    if x_turnstile:
        headers["x-turnstile"] = x_turnstile

    last_exc: Optional[Exception] = None
    for attempt in range(RETRY_ATTEMPTS + 1):
        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as c:
                r = await c.post(url, headers=headers, json={"q": q})
            if r.status_code in RETRY_STATUSES:
                logger.warning("edge 5xx on attempt %d: %s", attempt + 1, r.status_code)
                await asyncio.sleep(0.3 * (2 ** attempt))
                continue
            break
        except httpx.RequestFailed as e:
            last_exc = e
            logger.warning("edge request failed (attempt %d): %s", attempt + 1, e)
            await asyncio.sleep(0.3 * (2 ** attempt))
    else:
        raise HTTPException(status_code=502, detail=f"edge_unreachable: {last_exc}")

    # Best-effort JSON parse; include fallback text snippet on failure
    try:
        data = r.json()
    except Exception:
        logger.warning("edge non-JSON response status=%s ct=%r", r.status_code, r.headers.get("content-type"))
        data = {"detail": "bad_edge_response", "status": r.status_code, "text": r.text[:300]}

    if r.status_code >= 400:
        logger.warning("edge error %s for /translate/pro (len=%d)", r.status_code, len(q))
        # propagate edge status & message
        raise HTTPException(status_code=r.status_code, detail=data.get("detail", data))

    return data
