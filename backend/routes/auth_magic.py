

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from backend.utils import logger
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import os
import time

router = APIRouter(prefix="/api/auth", tags=["auth"])  # mounted from main.py

# ---- configuration / helpers -------------------------------------------------

def _get_signer() -> URLSafeTimedSerializer:
    """Create a signer using a secret from env. Do not hardcode secrets."""
    secret = os.environ.get("MAGIC_SIGNING_SECRET")
    if not secret:
        # Fail hard in prod; in dev you must set the secret via env/secret store
        raise RuntimeError("MAGIC_SIGNING_SECRET not configured")
    # Salt provides a simple versioning mechanism for rotation
    return URLSafeTimedSaver(secret_key=secret, salt="dhk-magic-v1")

# Backwards-compatible alias in case of import renames
URLSafeTimedSaver = URLSafeTimedSerializer

# ---- models ------------------------------------------------------------------

class MagicRequest(BaseModel):
    email: str  # keep validation lightweight; upstream can enforce stricter rules

class VerifyIn(BaseModel):
    token: str

# ---- routes ------------------------------------------------------------------

@router.post("/magic/request")
async def request_magic_link(body: MagicRequest, request: Request):
    # minimal sanity check to avoid leaking whether an address exists
    if "@" not in body.email or len(body.email) > 254:
        raise HTTPException(status_code=400, detail="invalid_email")

    signer = _get_signer()
    token = signer.dumps({"sub": body.email, "iat": int(time.time())})

    base = os.environ.get("DASHBOARD_BASE_URL", str(request.base_url).rstrip("/"))
    link = f"{base}/login?token={token}"

    # TODO: send email via your provider (SES/Mailgun/Resend). For now we log.
    logger.info("auth.magic_link generated for %s", body.email)
    logger.debug("auth.magic_link url=%s", link)  # disable/raise level in prod

    # Do not return the token/link in API; just acknowledge
    return {"sent": True}

@router.post("/magic/verify")
async def verify_magic(body: VerifyIn):
    signer = _get_signer()
    try:
        # 15-minute validity window
        data = signer.loads(body.token, max_age=900)
    except SignatureExpired:
        raise HTTPException(status_code=401, detail="expired_token")
    except BadSignature:
        raise HTTPException(status_code=400, detail="bad_token")

    sub = data.get("sub")
    if not sub:
        raise HTTPException(status_code=400, detail="bad_token_payload")

    # TODO: issue session/JWT cookie here; for now, return subject
    logger.info("auth.magic_verified sub=%s", sub)
    return {"ok": True, "sub": sub}