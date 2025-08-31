from dotenv import load_dotenv; load_dotenv()
import os, time, re, html, json, hashlib
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from backend.scripts.secure_log import secure_log

CORS = [o.strip() for o in os.getenv("CORS_ORIGINS","").split(",") if o.strip()]
API_KEYS = {k.strip() for k in os.getenv("API_KEYS","").split(",") if k.strip()}

BUCKET = {}               # (ip,fprint) -> timestamps
FAILED = {}               # ip -> (count, first_ts)
BLACKLIST = set()
LIMIT, WINDOW = 60, 60    # 60 req/min per (ip,fprint)
MAX_BODY = 2048           # 2KB POST cap
BAN_FAILS, BAN_WINDOW = 5, 300  # 5 bad in 5 min -> temp ban

def _sanitize(s: str) -> str:
    s = re.sub(r'(--|;|\bUNION\b|\bSELECT\b|\bDROP\b|\bINSERT\b|\bUPDATE\b)', '', s, flags=re.I)
    s = s.replace('../','').replace('..\\','')
    return html.escape(s)

def _fp(request):
    ua = request.headers.get('user-agent','') or ''
    acc = request.headers.get('accept','') or ''
    lang= request.headers.get('accept-language','') or ''
    return hashlib.sha256(f"{ua}|{acc}|{lang}".encode()).hexdigest()[:16]

def _headers(h):
    h["X-Content-Type-Options"] = "nosniff"
    h["X-Frame-Options"]        = "DENY"
    h["Referrer-Policy"]        = "strict-origin-when-cross-origin"
    h["Content-Security-Policy"]= "default-src 'self'"
    h["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

def _fail(ip: str):
    count, first = FAILED.get(ip, (0, time.time()))
    now = time.time()
    if now - first > BAN_WINDOW:
        count, first = 0, now
    count += 1
    if count >= BAN_FAILS:
        BLACKLIST.add(ip)
        secure_log("temp_ban_set", {"ip": ip}, "ERROR")
    FAILED[ip] = (count, first)

class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        ip = request.client.host if request.client else "unknown"
        if ip in BLACKLIST:
            secure_log("temp_ban_block", {"ip": ip}, "ERROR")
            return JSONResponse({"detail":"Temporarily banned"}, status_code=403)

        # CORS allowlist
        origin = request.headers.get("origin")
        if origin and CORS and origin not in CORS:
            secure_log("cors_block", {"ip": ip, "origin": origin}, "WARN")
            return JSONResponse({"detail":"CORS blocked"}, status_code=403)

        # Methods / body checks
        if request.method not in ("GET","POST","OPTIONS"):
            return JSONResponse({"detail":"Method not allowed"}, status_code=405)

        if request.method == "POST":
            body = await request.body()
            if len(body) > MAX_BODY:
                secure_log("bad_request", {"ip": ip, "reason": "payload_too_large"}, "WARN")
                return JSONResponse({"detail":"Payload too large"}, status_code=413)
            if not request.headers.get("content-type","").lower().startswith("application/json"):
                secure_log("bad_request", {"ip": ip, "reason": "wrong_content_type"}, "WARN")
                return JSONResponse({"detail":"Content-Type must be application/json"}, status_code=415)
            # Strict JSON schema
            try:
                data = json.loads(body.decode("utf-8"))
                if not isinstance(data, dict):
                    raise ValueError("Expected object")
                txt = data.get("text","")
                if not isinstance(txt, str) or len(txt) == 0 or len(txt) > 1000:
                    raise ValueError("Invalid text")
                data["text"] = _sanitize(txt)
                request._body = json.dumps(data).encode("utf-8")
            except Exception as err:
                _fail(ip)
                secure_log("bad_request", {"ip": ip, "error": str(err)}, "WARN")
                return JSONResponse({"detail":"Invalid JSON"}, status_code=400)

        # Rate limit (IP + fingerprint)
        key = (ip, _fp(request)); now = time.time()
        bucket = BUCKET.setdefault(key, [])
        while bucket and bucket[0] < now - WINDOW:
            bucket.pop(0)
        if len(bucket) >= LIMIT:
            secure_log("rate_limited", {"ip": ip}, "WARN")
            return JSONResponse({"detail":"Rate limit exceeded"}, status_code=429)
        bucket.append(now)

        # Pro gate
        if request.url.path.startswith("/translate/pro"):
            api_key = request.headers.get("x-api-key") or request.headers.get("authorization","").replace("Bearer ","")
            if (not api_key) or (api_key not in API_KEYS):
                _fail(ip)
                secure_log("auth_fail", {"ip": ip}, "WARN")
                return JSONResponse({"detail":"API key required"}, status_code=401)

        resp = await call_next(request)
        _headers(resp.headers)
        return resp
