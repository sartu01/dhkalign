

# Security Policy

*Last Updated: September 2025*
**Origin privacy**: backend origin is private; Cloudflare Worker is the only ingress for client traffic.
See also: **[Privacy Policy](./PRIVACY.md)** for data handling commitments.

## 📣 Reporting a Vulnerability
- Email **admin@dhkalign.com** with subject `SECURITY`
- Include: affected version/commit, PoC steps, expected vs actual, impact, minimal logs
- Please do **not** open public issues for security bugs
- **Acknowledgement SLA**: within 72 hours
- **Remediation targets**: Critical 72h • High 7d • Medium 30d • Low next release

## 🎯 Security Model

DHK Align implements a **defense-in-depth** security architecture with privacy as the primary objective.

### Core Security Principles

1. **Free-first, local-first**: Free tier (safety ≤ 1) runs from client cache/in-browser; backend is minimized for free.
2. **Hidden backend**: All backend traffic flows only through the Cloudflare Worker; origin never accepts direct public traffic.
3. **Zero trust inputs**: Validate, sanitize, cap; never trust user input or model output.
4. **Least data / No PII**: No user identifiers stored; logs contain no raw text; redaction on any diagnostic previews.
5. **Defense in depth**: Edge rate-limit + origin rate-limit, CORS allowlist, security headers, API-key gate, payload caps, temp bans, KV/TTL caches.
6. **Tamper‑evident operations**: HMAC‑signed append‑only audit logs and nightly backups with restore drills.

### Hidden Backend & Edge Shield (Deployed Posture)

- **Cloudflare Worker (edge)** sits in front of the origin; only these paths are forwarded:
  - "/health" (origin health)
  - "/translate", "/translate/pro" (API)
  - "/admin/health", "/admin/cache_stats" (admin surfaces, key-gated at edge)
- **Origin** is private: DNS is orange‑clouded; if needed, Cloudflare Tunnel is used. No other ingress is allowed.
- **Edge cache / usage** (KV bindings):
  - `CACHE` — TTL response cache for `/translate*` (header: `CF-Cache-Edge: HIT|MISS`)
  - `USAGE` — per-API-key daily counters (rolling ~40h TTL)
- **KV-backed edge rate‑limit**: minute‑bucket per IP via KV; origin also rate‑limits (IP + fingerprint) at 60/min.
- **API key** is required for `/translate/pro`; free `/translate` never serves `safety_level ≥ 2`.
- **Backend TTL cache**: In‑process cache adds `X-Backend-Cache: HIT|MISS` when edge cache is bypassed with `?cache=no`.

### Data Classification & Retention

- **Safety levels**: `≤ 1` (safe/free), `≥ 2` (pro: slang, profanity, dialects).
- **Free tier** returns only safety ≤ 1; **Pro tier** exposes ≥ 2 with `pack` filter.
- **Logs**: HMAC‑signed JSONL at `private/audit/security.jsonl`; contain event type, IP, and metadata — **no raw user text**. Redaction helper is used for any necessary previews.
- **Edge KV cache**: response bodies cached briefly (default 5 minutes) for `/translate*`; bypass with `?cache=no`.
- **KV usage metering**: counters stored as `usage:{key}:{YYYY-MM-DD}` with ~40h rolling TTL; exported to private store if billing is enabled.
- **Backups**: nightly SQLite backups to `private/backups/YYYY-MM-DD_translations.db`; restore drill documented.
- **Retention**: audit logs and backups kept locally; off‑box copies only on explicit ops action. Edge KV is not used for audit logs.

## 🛡️ Threat Model

### In Scope Threats

| Threat | Risk Level | Mitigation | Implementation |
|--------|------------|------------|----------------|
| **XSS Attacks** | High | Input sanitization, CSP headers | React escaping; CSP; sanitizer in frontend; headers in middleware |
| **CSRF Attacks** | Medium | SameSite cookies, origin checks, double-submit tokens (if cookies used) | Not applicable for tokenless JSON POST; CORS allowlist in middleware |
| **Injection Attacks** | High | Parameterized queries, input validation | Pydantic validation; parameterized SQLite queries; sanitize in middleware |
| **DoS/DDoS** | Medium | Rate limiting, CDN protection | Cloudflare Worker KV rate‑limit + origin rate‑limit (security_middleware.py) |
| **Data Leakage** | High | Encryption, minimal logging | No PII in logs; HMAC audit (secure_log.py); safety gating |
| **Session Hijacking** | Medium | Secure cookies, short TTL (if cookies used) | No session cookies by default; API key header on pro only |
| **MitM** | High | HTTPS enforcement, HSTS | HTTPS (CF) + HSTS headers in middleware/edge |

### Out of Scope (v1)

- Nation-state level attacks
- Physical security breaches
- Supply chain attacks on dependencies
- Zero-day exploits in browsers
- Social engineering attacks

## 🔐 Security Measures

### Frontend Security

#### Input Sanitization

```javascript
// Input Sanitization (src/utils/sanitizer.js)
export function sanitizeInput(text) {
  if (!text || typeof text !== 'string') return '';
  
  return text
    .trim()
    .slice(0, 200)                      // Length limit
    .replace(/[\x00-\x1F\x7F]/g, '')    // Control characters
    .replace(/[<>&"']/g, (char) => ({   // HTML entities
      '<': '&lt;',
      '>': '&gt;',
      '&': '&amp;',
      '"': '&quot;',
      "'": '&#39;'
    })[char])
    .replace(/\s+/g, ' ');              // Normalize whitespace
}
```

#### Content Security Policy

```html
<!-- Strict CSP for XSS prevention (nonce-based) -->
<meta http-equiv="Content-Security-Policy"
      content="default-src 'self';
               script-src 'self' https://js.stripe.com 'nonce-__NONCE__';
               style-src 'self' 'nonce-__NONCE__';
               img-src 'self' data: https:;
               connect-src 'self' https://dhkalign.com;
               frame-src https://js.stripe.com;
               object-src 'none';
               base-uri 'self';">
```
> Use a runtime-generated nonce and attach it to allowed inline tags. Avoid `'unsafe-inline'`.


#### Subresource Integrity (SRI)

```html
<!-- Example: SRI for third-party script -->
<script src="https://js.stripe.com/v3" 
        integrity="sha384-REPLACE_WITH_STRIPE_SRI_HASH" 
        crossorigin="anonymous" nonce="__NONCE__"></script>
```
> Use SRI for any third-party scripts when a fixed version is known. Keep nonce + SRI aligned during deploys.

#### Generate SRI Hash (sha384)

```bash
# Using curl + openssl
curl -sSL https://js.stripe.com/v3 \
  | openssl dgst -sha384 -binary \
  | openssl base64 -A

# Output → paste into: integrity="sha384-<HASH>"
```
> Re-run when the third‑party script version changes. Commit the new hash alongside the version bump.

#### Generating CSP Nonces (FastAPI)

```python
# CSP Nonce middleware (FastAPI / Starlette)
import secrets
from starlette.middleware.base import BaseHTTPMiddleware

class CSPNonceMiddleware(BaseHTTPMiddleware):
  async def dispatch(self, request, call_next):
    nonce = secrets.token_urlsafe(16)
    request.state.csp_nonce = nonce
    response = await call_next(request)
    # Expose for templating/log checks (remove in production if not needed)
    response.headers["X-CSP-Nonce"] = nonce
    return response

# app.add_middleware(CSPNonceMiddleware)
```
> Attach "+ nonce +" to any inline <script> or <style> tags (e.g., via your template/SSR). Avoid 'unsafe-inline'.

#### Secure State Management

```javascript
// Minimal, non-secret storage wrapper (no encryption; never store secrets)
export const storage = {
  set: (key, value) => {
    try {
      // Store only non-sensitive preferences/caches
      sessionStorage.setItem(key, JSON.stringify(value));
    } catch (error) {
      console.warn('Storage write failed:', error);
    }
  },
  get: (key) => {
    try {
      const raw = sessionStorage.getItem(key);
      return raw ? JSON.parse(raw) : null;
    } catch (error) {
      console.warn('Storage read failed:', error);
      return null;
    }
  },
  remove: (key) => {
    sessionStorage.removeItem(key);
  }
};
```
> Do not store secrets or raw user text in browser storage. Encryption with hardcoded keys (e.g., fallbacks) is prohibited.

### Backend Security

**Reality note**: The backend is not publicly reachable. All examples assume calls arrive via the Cloudflare Worker. Direct origin access is disabled in production.

#### Rate Limiting

```python
# Rate Limiting (app/utils/rate_limit.py)
from fastapi import Request, HTTPException
from collections import defaultdict
import time

class RateLimiter:
    def __init__(self, requests: int = 100, window: int = 60):
        self.requests = requests
        self.window = window
        self.clients = defaultdict(list)
    
    async def check_rate_limit(self, request: Request):
        client_ip = self._get_client_ip(request)
        now = time.time()
        
        # Clean old requests
        self.clients[client_ip] = [
            req_time for req_time in self.clients[client_ip]
            if req_time > now - self.window
        ]
        
        # Check rate limit
        if len(self.clients[client_ip]) >= self.requests:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later.",
                headers={"Retry-After": str(self.window)}
            )
        
        self.clients[client_ip].append(now)
    
    def _get_client_ip(self, request: Request) -> str:
        # Handle proxy headers safely
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host
```

#### Input Validation

```python
# Comprehensive input validation
from pydantic import BaseModel, validator, Field
from typing import Optional
import re

class TranslationRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=200)
    session_id: Optional[str] = Field(None, regex=r'^[a-f0-9-]{36}$')
    
    @validator('text')
    def validate_text(cls, v):
        # Remove control characters
        cleaned = re.sub(r'[\x00-\x1F\x7F]', '', v)
        
        # Check for potential XSS patterns
        dangerous_patterns = [
            r'<script', r'javascript:', r'data:text/html',
            r'vbscript:', r'onload=', r'onerror='
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, cleaned, re.IGNORECASE):
                raise ValueError('Invalid input detected')
        
        return cleaned.strip()
    
    @validator('session_id')
    def validate_session_id(cls, v):
        if v and not re.match(r'^[a-f0-9-]{36}$', v):
            raise ValueError('Invalid session ID format')
        return v

class FeedbackRequest(BaseModel):
    input_text: str = Field(..., min_length=1, max_length=500)
    expected: str = Field(..., min_length=1, max_length=500)
    actual: str = Field(..., min_length=1, max_length=500)
    rating: int = Field(..., ge=1, le=5)
    comments: Optional[str] = Field(None, max_length=1000)
    
    @validator('*', pre=True)
    def sanitize_strings(cls, v):
        if isinstance(v, str):
            # Basic sanitization
            return re.sub(r'[\x00-\x1F\x7F]', '', v).strip()
        return v
```

#### CORS Configuration

```python
# Secure CORS setup
import os
from fastapi.middleware.cors import CORSMiddleware

def setup_cors(app):
    allowed_origins = [
        "https://dhkalign.com",
        "https://www.dhkalign.com",
        "http://localhost:3000",  # Development only
    ]
    
    # Remove localhost in production
    if os.getenv("ENVIRONMENT") == "production":
        allowed_origins = [origin for origin in allowed_origins 
                          if not origin.startswith("http://localhost")]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Authorization"],
        expose_headers=["X-Request-ID"],
        max_age=3600,  # Cache preflight for 1 hour
    )
```

### Infrastructure Security

#### Security Headers

```nginx
# nginx security headers
server {
    listen 443 ssl http2;
    server_name dhkalign.com;
    
    # SSL Configuration
    ssl_certificate /etc/ssl/certs/dhkalign.pem;
    ssl_certificate_key /etc/ssl/private/dhkalign.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security Headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    
    # Content Security Policy
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' https://js.stripe.com 'nonce-__NONCE__'; style-src 'self' 'nonce-__NONCE__'; img-src 'self' data: https:; connect-src 'self' https://dhkalign.com https://api.dhkalign.com; frame-src https://js.stripe.com; object-src 'none'; base-uri 'self'" always;
    
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Security
        proxy_hide_header X-Powered-By;
        proxy_set_header X-Request-ID $request_id;
    }
    
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Rate limiting
        limit_req zone=api burst=20 nodelay;
        limit_req_status 429;
        
        # Timeouts
        proxy_connect_timeout 5s;
        proxy_send_timeout 10s;
        proxy_read_timeout 10s;
    }
}

# Place rate limiting zones inside the top-level http {} context in nginx.conf
# Rate limiting zones
http {
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=general:10m rate=5r/s;
}
```

#### Docker Security

```dockerfile
# Secure Dockerfile
FROM python:3.11-slim

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Install dependencies as root
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Set proper permissions
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Security: Don't run as root
# Security: Use specific port
EXPOSE 8000

# Security: Use exec form
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml with security settings
version: '3.8'

services:
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/dhkalign
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    restart: unless-stopped
    
  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/ssl:ro
    security_opt:
      - no-new-privileges:true
    restart: unless-stopped
```

## 🔍 Security Monitoring

### Automated Security Scanning

```bash
# Security audit pipeline
#!/bin/bash

echo "🔍 Running security audit..."

# Frontend security
cd frontend
npm audit --audit-level moderate
npm run lint

# Backend security  
cd ../backend
pip-audit
bandit -r app/
safety check

# Container security
trivy image dhkalign/backend:latest

# SAST scanning
semgrep --config=auto .

echo "✅ Security audit complete"
```

### Security Logging

```python
# Security event logging
import structlog
from datetime import datetime

security_logger = structlog.get_logger("security")

class SecurityLogger:
    @staticmethod
    def log_rate_limit_exceeded(request, attempts):
        security_logger.warning(
            "rate_limit_exceeded",
            client_ip=request.client.host,
            endpoint=request.url.path,
            attempts=attempts,
            user_agent=request.headers.get("user-agent", ""),
            timestamp=datetime.utcnow().isoformat()
        )
    
    @staticmethod
    def log_invalid_input(request, input_data, validation_error):
        security_logger.warning(
            "invalid_input_detected",
            client_ip=request.client.host,
            endpoint=request.url.path,
            input_length=len(str(input_data)),
            error=str(validation_error),
            timestamp=datetime.utcnow().isoformat()
        )
    
    @staticmethod
    def log_suspicious_activity(request, activity_type, details):
        security_logger.error(
            "suspicious_activity",
            client_ip=request.client.host,
            activity_type=activity_type,
            details=details,
            user_agent=request.headers.get("user-agent", ""),
            timestamp=datetime.utcnow().isoformat()
        )
```
**Policy:** Never log raw user text or identifiers. Always redact before logging.

```python
# Minimal redaction helper for logs
import re

_REDACT_PATTERNS = [
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+"), "[email]"),
    (re.compile(r"\b\d{9,16}\b"), "[number]"),  # long numeric sequences
]

def redact(value: str) -> str:
    if not isinstance(value, str):
        return value
    out = value
    for pat, repl in _REDACT_PATTERNS:
        out = pat.sub(repl, out)
    return out[:512]  # cap length
```
```python
# Example: security_logger.warning("invalid_input", preview=redact(user_input))
```

### Intrusion Detection

```python
# Simple intrusion detection
import re
from collections import defaultdict
from fastapi import HTTPException

class IntrusionDetector:
    def __init__(self):
        self.suspicious_patterns = [
            r'union\s+select',
            r'<script[^>]*>',
            r'javascript:',
            r'../../../',
            r'cmd\.exe',
            r'/etc/passwd'
        ]
        self.failed_attempts = defaultdict(int)
        self.blocked_ips = set()
    
    def analyze_request(self, request):
        client_ip = request.client.host
        request_data = str(request.url) + str(request.headers)
        
        # Check for suspicious patterns
        for pattern in self.suspicious_patterns:
            if re.search(pattern, request_data, re.IGNORECASE):
                self._handle_suspicious_activity(
                    client_ip, 
                    f"Suspicious pattern detected: {pattern}"
                )
                return False
        
        # Check if IP is blocked
        if client_ip in self.blocked_ips:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return True
    
    def _handle_suspicious_activity(self, client_ip, reason):
        self.failed_attempts[client_ip] += 1
        
        SecurityLogger.log_suspicious_activity(
            request=None,  # Would need to pass request
            activity_type="pattern_match",
            details=reason
        )
        
        # Block IP after 5 suspicious attempts
        if self.failed_attempts[client_ip] >= 5:
            self.blocked_ips.add(client_ip)
            SecurityLogger.log_suspicious_activity(
                request=None,
                activity_type="ip_blocked",
                details=f"IP {client_ip} blocked after {self.failed_attempts[client_ip]} attempts"
            )
```

## 🚨 Incident Response

### Response Plan

1. **Detection**: Automated alerts via monitoring
2. **Assessment**: Evaluate severity and scope within 30 minutes
3. **Containment**: Isolate affected systems within 1 hour
4. **Eradication**: Remove threat and patch vulnerabilities
5. **Recovery**: Restore services and monitor for recurrence
6. **Lessons Learned**: Post-mortem analysis within 48 hours

### Emergency Contacts

- **Security Contact**: admin@dhkalign.com (use subject "SECURITY")
- **Target Response**: 1 hour (critical) / 24 hours (high)

### Incident Classification

| Severity | Description | Response Time | Examples |
|----------|-------------|---------------|----------|
| **Critical** | Service compromise, data breach | 1 hour | RCE, data exfiltration |
| **High** | Security vulnerability affecting users | 4 hours | XSS, privilege escalation |
| **Medium** | Security issue with limited impact | 24 hours | Information disclosure |
| **Low** | Minor security concern | 72 hours | Missing security headers |

## 🐛 Vulnerability Disclosure

### Responsible Disclosure Process

1. **Report**: Email admin@dhkalign.com with subject "SECURITY" and include:
   - Description of vulnerability
   - Steps to reproduce
   - Potential impact assessment
   - Suggested remediation (if any)

2. **Acknowledgment**: We'll respond within 72 hours

3. **Investigation**: Initial assessment within 7 days

4. **Resolution**: Fix timeline based on severity:
   - Critical: 72 hours
   - High: 7 days
   - Medium: 30 days
   - Low: Next regular release

5. **Disclosure**: Public disclosure after 90 days or fix deployment

### Bug Bounty Guidelines

| Severity | Payout Range | Examples |
|----------|--------------|----------|
| **Critical** | $200-500 | RCE, Authentication bypass |
| **High** | $100-200 | XSS, SQL injection |
| **Medium** | $50-100 | CSRF, Information disclosure |
| **Low** | $10-50 | Missing security headers |

#### Scope

**In Scope:**
- DHK Align web application (dhkalign.com)
- Frontend client-side vulnerabilities
- Backend API vulnerabilities
- Infrastructure misconfigurations

**Out of Scope:**
- Third-party services (Stripe, etc.)
- Social engineering attacks
- Physical security
- DoS/DDoS attacks
- Issues requiring physical access

#### Rules

- No data destruction or privacy violations
- Don't access other users' data
- Report findings immediately
- Don't publicly disclose until resolved
- One report per vulnerability

## 🔧 Security Checklist

### Development Security

- [ ] Input validation on all user inputs
- [ ] Output encoding for all dynamic content
- [ ] Parameterized queries (no SQL injection)
- [ ] Secure session management
- [ ] Proper error handling (no information leakage)
- [ ] Security headers configured
- [ ] HTTPS enforced everywhere
- [ ] Secrets managed securely
- [ ] Dependencies regularly updated
- [ ] Security tests included

### Deployment Security

- [ ] SSL/TLS certificates valid and current
- [ ] Security headers configured in web server
- [ ] Database connections encrypted
- [ ] Secrets stored in environment variables
- [ ] Non-root containers
- [ ] Network segmentation
- [ ] Monitoring and alerting active
- [ ] Backup encryption enabled
- [ ] Access logs configured
- [ ] Incident response plan ready

### Regular Maintenance

- [ ] Weekly dependency updates
- [ ] Monthly security scans
- [ ] Quarterly penetration tests
- [ ] Annual security audit
- [ ] Regular backup testing
- [ ] Security training for team
- [ ] Incident response drills
- [ ] Access review and cleanup

## 📚 Security Resources

### Documentation
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [React Security Best Practices](https://snyk.io/blog/10-react-security-best-practices/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [Docker Security](https://docs.docker.com/engine/security/)

### Tools
- [OWASP ZAP](https://www.zaproxy.org/) - Web application security scanner
- [Semgrep](https://semgrep.dev/) - Static analysis security scanner
- [Bandit](https://bandit.readthedocs.io/) - Python security linter
- [npm audit](https://docs.npmjs.com/cli/v8/commands/npm-audit) - Node.js security auditing

---

<div align="center">
  <p><strong>Security is everyone's responsibility</strong></p>
  <p>Report security issues to: admin@dhkalign.com (subject: SECURITY)</p>
</div>