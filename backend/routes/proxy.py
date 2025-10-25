import os
import httpx
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

router = APIRouter()
EDGE_DEFAULT = "https://edge.dhkalign.com"

class Body(BaseModel):
  q: str

@router.post("/api/pro-translate")
async def pro_translate(
    b: Body,
    x_turnstile: str | None = Header(default=None, convert_underscores=False),
):
    q = (b.q or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="empty_query")

    # Read current env each call so key rotations take effect without restart
    EDGE = os.getenv("EDGE_BASE_URL", EDGE_DEFAULT)
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

    try:
        async with httpx.AsyncClient(timeout=12.0) as c:
            r = await c.post(f"{EDGE}/translate/pro", headers=headers, json={"q": q})
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"edge_error: {e}")

    # Best-effort JSON parse; include fallback text snippet on failure
    try:
        data = r.json()
    except Exception:
        data = {"detail": "bad_edge_response", "status": r.status_code, "text": r.text[:300]}

    if r.status_code >= 400:
        # propagate edge status & message
        raise HTTPException(status_code=r.status_code, detail=data.get("detail", data))

    return data
