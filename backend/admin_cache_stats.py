from fastapi import APIRouter
from backend import middleware_cache as mc

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/cache_stats")
async def cache_stats():
    inst = getattr(mc, "LAST_INSTANCE", None)
    if inst is None:
        return {"cache_hits": 0, "cache_misses": 0, "note": "middleware not initialized"}
    return mc.backend_cache_stats(inst)
