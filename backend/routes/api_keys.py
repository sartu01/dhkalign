import os
import secrets
import json
import hashlib
import time
import pathlib
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.utils import logger

router = APIRouter(prefix="/api/keys", tags=["keys"])

# Basic file-backed key store (replace with DB later)
STORE_PATH = pathlib.Path(os.getenv("KEY_STORE_PATH", "/data/keys.json"))
SALT = (os.getenv("API_KEY_SALT") or "dev-salt").encode()

# Hashing settings (versioned)
ALG_ID = "pbkdf2_sha256_v1"
PBKDF_ITERATIONS = int(os.getenv("API_KEY_PBKDF_ITERS", "200000"))

STORE_PATH.parent.mkdir(parents=True, exist_ok=True)

def _load_store() -> dict:
    if not STORE_PATH.exists():
        return {"keys": []}
    try:
        return json.loads(STORE_PATH.read_text())
    except Exception:
        logger.warning("api_keys.load_store failed, recreating empty store")
        return {"keys": []}

def _save_store(d: dict) -> None:
    STORE_PATH.write_text(json.dumps(d))

def _hash(api_key: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        api_key.encode("utf-8"),
        SALT,
        PBKDF_ITERATIONS,
        dklen=32,
    ).hex()

# --- Models -----------------------------------------------------------------
class CreateKeyIn(BaseModel):
    note: Optional[str] = None
    ttl_seconds: Optional[int] = None

class RotateKeyIn(BaseModel):
    id: str
    note: Optional[str] = None

class VerifyKeyIn(BaseModel):
    key: str

# --- Routes -----------------------------------------------------------------
@router.post("/create")
async def create_key(body: CreateKeyIn):
    raw = secrets.token_urlsafe(32)
    record = {
        "id": secrets.token_hex(8),
        "hash": _hash(raw),
        "algo": ALG_ID,
        "note": body.note or "",
        "created_at": int(time.time()),
        "expires_at": int(time.time()) + body.ttl_seconds if body.ttl_seconds else None,
        "revoked": False,
    }
    store = _load_store()
    store["keys"].append(record)
    _save_store(store)
    masked = raw[:6] + "…" + raw[-4:]
    logger.info("api_key.created id=%s exp=%s", record["id"], record["expires_at"])
    return {"id": record["id"], "key": raw, "masked": masked}

@router.post("/rotate")
async def rotate_key(body: RotateKeyIn):
    store = _load_store()
    for rec in store.get("keys", []):
        if rec["id"] == body.id and not rec.get("revoked"):
            new_raw = secrets.token_urlsafe(32)
            rec["hash"] = _hash(new_raw)
            rec["rotated_at"] = int(time.time())
            if body.note is not None:
                rec["note"] = body.note
            _save_store(store)
            logger.info("api_key.rotated id=%s", body.id)
            return {"id": body.id, "key": new_raw}
    raise HTTPException(status_code=404, detail="not_found")

@router.post("/verify")
async def verify_key(body: VerifyKeyIn):
    store = _load_store()
    now = int(time.time())
    for rec in store.get("keys", []):
        algo = rec.get("algo", "blake2b_legacy")
        if algo == "pbkdf2_sha256_v1":
            expected = _hash(body.key)
        else:
            # legacy blake2b fallback for old records
            expected = hashlib.blake2b(body.key.encode(), key=SALT, digest_size=32).hexdigest()
        if (
            not rec.get("revoked")
            and rec.get("hash") == expected
            and (rec.get("expires_at") is None or rec["expires_at"] > now)
        ):
            return {"valid": True, "id": rec["id"], "note": rec.get("note")}
    return {"valid": False}