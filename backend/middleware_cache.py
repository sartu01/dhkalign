import os, json, asyncio, time, hashlib
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

def _now(): return time.time()
def _sha(s: bytes) -> str: return hashlib.sha256(s).hexdigest()

LAST_INSTANCE = None

class TTLResponseCacheMiddleware(BaseHTTPMiddleware):
    """
    Caches successful JSON responses for /translate*.
    Key = method + path + query + body_hash.
    Bypass with ?cache=no. TTL via BACKEND_CACHE_TTL (default 120s).
    Adds header: X-Backend-Cache: HIT|MISS.
    """
    def __init__(self, app):
        global LAST_INSTANCE
        super().__init__(app)
        LAST_INSTANCE = self
        self.ttl = int(os.getenv("BACKEND_CACHE_TTL", "120"))
        self._store = {}  # key -> (expires_at, status, headers_dict, body_bytes)
        self._lock = asyncio.Lock()
        # lightweight counters
        self.counters = {"cache_hits": 0, "cache_misses": 0}

    async def dispatch(self, request, call_next):
        url = request.url
        if not url.path.startswith("/translate"):  # only cache translate endpoints
            return await call_next(request)

        if request.query_params.get("cache") == "no":
            resp = await call_next(request)
            return self._tag(resp, "MISS-bypass")

        method = request.method.upper()
        body_bytes = b""
        if method in ("POST", "PUT", "PATCH"):
            body_bytes = await request.body()
            # re-inject body for downstream since reading consumes it
            async def _receive():
                return {"type": "http.request", "body": body_bytes, "more_body": False}
            request._receive = _receive  # type: ignore

        key_str = f"{method}:{url.path}?{url.query}:{_sha(body_bytes)}"
        key = _sha(key_str.encode())

        async with self._lock:
            ent = self._store.get(key)
            if ent and ent[0] > _now():
                self.counters["cache_hits"] += 1
                status, headers, body = ent[1], ent[2], ent[3]
                resp = Response(content=body, status_code=status, headers=headers)
                return self._tag(resp, "HIT")

        # miss: call downstream
        resp = await call_next(request)

        # cache only successful JSON with small/medium bodies
        try:
            ct = (resp.headers.get("content-type") or "").lower()
            if 200 <= resp.status_code < 300 and "application/json" in ct:
                body = await resp.body()
                # rebuild response after reading
                new_resp = Response(content=body, status_code=resp.status_code, headers=dict(resp.headers))
                async with self._lock:
                    self._store[key] = (_now() + self.ttl, new_resp.status_code, dict(new_resp.headers), body)
                    self.counters["cache_misses"] += 1
                return self._tag(new_resp, "MISS")
        except Exception:
            pass

        return self._tag(resp, "MISS")

    def _tag(self, resp: Response, tag: str) -> Response:
        resp.headers["X-Backend-Cache"] = tag
        return resp

# helper to expose counters
def backend_cache_stats(mw: "TTLResponseCacheMiddleware"):
    return dict(mw.counters)
