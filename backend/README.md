
# DHK Align - Backend (FastAPI)
*Optional public-facing FastAPI service for analytics, feedback, health checks, and API fallback. Translation stays client-side.*

[![FastAPI](https://img.shields.io/badge/FastAPI-0.1x-009688.svg)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](../LICENSE)

Optional FastAPI service for DHK Align providing:
- **📊 Analytics collection** (anonymous usage stats)
- **💬 Feedback submission** (translation improvements)
- **🔍 Health monitoring** (system status)
- **📡 API fallback** (when client-side fails)


## 🔓 Public Deployment Notes

This document is **safe to publish** for users and collaborators. To protect your IP and data:

- This backend **does not perform translations**. All translations happen **client-side**.
- **No raw input text is persisted** by default. Only anonymized metrics (counts, durations, method, confidence) are logged.
- Keep the **backend repository private** (frontend can be public).
- Do **not** commit `.env` files, credentials, API keys, or datasets.
- Ensure logs contain **no raw user input**; store only anonymized metrics (counts, durations, methods, confidence).
- Configure **CORS** to only allow your production domain(s) and localhost during development.
- Rate limit all public endpoints and monitor error rates.
- If analytics are not desired, **disable them entirely** via env flags and remove routes at build time.
- If you later expose a paid API, gate it with API keys or OAuth and add per-key rate limits.

**Contacts:**  
Support — [info@dhkalign.com](mailto:info@dhkalign.com) • Admin — [admin@dhkalign.com](mailto:admin@dhkalign.com)
Security — admin@dhkalign.com (use subject "SECURITY")

## 🚀 Quick Start

```bash
# Setup environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .\.venv\Scripts\activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env

# Run development server (public build)
uvicorn main:app --reload --port 8000
```

Visit http://localhost:8000/docs for API documentation.

## 🏗️ Structure

```
backend/
├── app/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── translate.py     # Translation analytics
│   │   │   ├── feedback.py      # User feedback collection
│   │   │   └── health.py        # Health checks
│   │   └── deps.py              # Dependencies
│   ├── core/
│   │   ├── config.py            # Configuration
│   │   └── logging.py           # Structured logging
│   ├── models/
│   │   ├── feedback.py          # Pydantic models
│   │   └── analytics.py         # Analytics models
│   └── utils/
│       └── logger.py            # Logging utilities
├── logs/
│   ├── feedback.jsonl           # User feedback
│   ├── analytics.jsonl          # Usage analytics
│   └── errors.log              # Error logs
├── requirements.txt
├── main.py
└── README.md
```

## 🔌 API Endpoints

All endpoints are public and rate-limited; no authentication is required for the public build.

### Core Endpoints

| Endpoint                   | Method | Purpose                     | Auth Required |
|----------------------------|--------|-----------------------------|---------------|
| `/health`                  | GET    | System health check         | No            |
| `/api/translate/analytics` | POST   | Log translation usage       | No            |
| `/api/feedback`            | POST   | Submit translation feedback | No            |
| `/docs`                    | GET    | Interactive API docs        | No            |

### Translation Analytics

```http
POST /api/translate/analytics
Content-Type: application/json

{
  "session_id": "uuid",
  "method": "fuzzy",
  "confidence": 0.87,
  "duration_ms": 23,
  "cache_hit": false
}
```

**Response:**
```json
{
  "success": true,
  "message": "Analytics recorded"
}
```

### Feedback Collection

```http
POST /api/feedback
Content-Type: application/json

{
  "input": "ami valo achi",
  "expected": "I am fine", 
  "actual": "I am doing well",
  "rating": 4,
  "comments": "Good translation but could be more casual"
}
```

**Response:**
```json
{
  "success": true,
  "feedback_id": "fb_123456"
}
```

### Health Check

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime_seconds": 86400,
  "services": {
    "database": "connected",
    "logging": "operational"
  }
}
```

## ⚙️ Configuration

### Environment Variables

```bash
# .env.example
HOST=0.0.0.0
PORT=8000

# Database (optional - for feedback storage)
DATABASE_URL=sqlite:///./dhkalign.db
# Feedback persistence is optional. If no database is set, logs will still capture events.

# Logging
LOG_LEVEL=INFO
LOG_DIR=logs

# CORS
ALLOWED_ORIGINS=http://localhost:3000,https://dhkalign.com,https://www.dhkalign.com
# For multiple origins, use comma-separated values as shown above.

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# Features
ANALYTICS_ENABLED=true
FEEDBACK_ENABLED=true
```

### Basic Configuration

```python
# app/core/config.py
from pydantic import BaseSettings

class Settings(BaseSettings):
    app_name: str = "DHK Align Backend"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    
    # Optional database for feedback storage
    database_url: str = "sqlite:///./dhkalign.db"
    
    # CORS settings
    allowed_origins: list = ["http://localhost:3000"]
    
    class Config:
        env_file = ".env"

settings = Settings()
```

## 📊 Logging & Analytics

### Structured Logging

All events are logged as JSON Lines for easy parsing:

```json
// logs/analytics.jsonl
{
  "timestamp": "2024-01-27T10:30:45.123Z",
  "event": "translation_analytics",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "method": "fuzzy",
  "confidence": 0.87,
  "duration_ms": 23,
  "success": true
}

// logs/feedback.jsonl
{
  "timestamp": "2024-01-27T10:31:00.456Z",
  "event": "user_feedback",
  "feedback_id": "fb_123456",
  "rating": 4,
  "input_length": 14,
  "has_comments": true
}
```

### Log Analysis

```bash
# Real-time monitoring
tail -f logs/analytics.jsonl | jq '.'

# Count translation methods
cat logs/analytics.jsonl | jq -r '.method' | sort | uniq -c

# Average confidence by method
cat logs/analytics.jsonl | jq -r '.method + "," + (.confidence | tostring)' | \
  awk -F, '{sum[$1]+=$2; count[$1]++} END {for(i in sum) print i, sum[i]/count[i]}'
```

## 🧪 Testing

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest

# Run with coverage
pytest --cov=app tests/
```

### Example Tests

```python
# tests/test_api.py
import pytest
from httpx import AsyncClient
from main import app

@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

@pytest.mark.asyncio
async def test_analytics_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as client:
        analytics_data = {
            "session_id": "test-session",
            "method": "exact",
            "confidence": 1.0,
            "duration_ms": 10,
            "cache_hit": False
        }
        response = await client.post("/api/translate/analytics", json=analytics_data)
        assert response.status_code == 200
        assert response.json()["success"] is True

@pytest.mark.asyncio
async def test_feedback_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as client:
        feedback_data = {
            "input": "test input",
            "expected": "test expected",
            "actual": "test actual",
            "rating": 5
        }
        response = await client.post("/api/feedback", json=feedback_data)
        assert response.status_code == 200
        assert "feedback_id" in response.json()
```

## 🚀 Deployment

### Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:///./dhkalign.db
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    
  # Optional: Add database for persistent feedback storage
  # db:
  #   image: postgres:15
  #   environment:
  #     - POSTGRES_DB=dhkalign
  #     - POSTGRES_USER=dhkalign
  #     - POSTGRES_PASSWORD=password
  #   volumes:
  #     - postgres_data:/var/lib/postgresql/data

# volumes:
#   postgres_data:
```

### Production Deployment

```bash
# Build for production
docker build -t dhkalign-backend .

# Run with production settings
docker run -d \
  --name dhkalign-backend \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:pass@localhost/dhkalign \
  -e LOG_LEVEL=WARNING \
  -v /path/to/logs:/app/logs \
  dhkalign-backend
```

### Platform Deployment

#### Railway

```json
// railway.json
{
  "build": {
    "builder": "DOCKERFILE"
  },
  "deploy": {
    "startCommand": "uvicorn main:app --host 0.0.0.0 --port $PORT",
    "healthcheckPath": "/health"
  }
}
```

#### Heroku

```text
# Procfile
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

#### DigitalOcean App Platform

```yaml
# .do/app.yaml
name: dhkalign-backend
services:
- name: api
  source_dir: /
  github:
    repo: PRIVATE_BACKEND_REPO   # keep backend repo private
    branch: main
  run_command: uvicorn main:app --host 0.0.0.0 --port $PORT
  environment_slug: python
  instance_count: 1
  instance_size_slug: basic-xxs
  http_port: 8000
  health_check:
    http_path: /health
  envs:
  - key: LOG_LEVEL
    value: INFO
```

## 🔍 Monitoring

### Health Monitoring

```python
# app/utils/monitoring.py
import asyncio
import time
from typing import Dict

class HealthMonitor:
    """Simple health monitoring for public deployment"""
    
    @staticmethod
    async def get_system_health() -> Dict:
        """Get basic system health metrics"""
        start_time = time.time()
        
        # Basic checks
        checks = {
            "api": True,  # If we're running, API is up
            "logging": await HealthMonitor._check_logging(),
            "storage": await HealthMonitor._check_storage()
        }
        
        response_time = (time.time() - start_time) * 1000
        
        return {
            "status": "healthy" if all(checks.values()) else "degraded",
            "checks": checks,
            "response_time_ms": response_time,
            "uptime_seconds": time.time() - HealthMonitor._start_time
        }
    
    @staticmethod
    async def _check_logging() -> bool:
        """Check if logging is working"""
        try:
            import logging
            logging.info("Health check log test")
            return True
        except Exception:
            return False
    
    @staticmethod
    async def _check_storage() -> bool:
        """Check if log directory is writable"""
        try:
            import os
            log_dir = "logs"
            return os.path.exists(log_dir) and os.access(log_dir, os.W_OK)
        except Exception:
            return False

# Initialize start time
HealthMonitor._start_time = time.time()
```

### Simple Metrics

```python
# app/utils/metrics.py
from collections import defaultdict
import json
import time

class SimpleMetrics:
    """Basic metrics collection for public deployment"""
    
    def __init__(self):
        self.request_count = defaultdict(int)
        self.response_times = []
        self.error_count = 0
        
    def record_request(self, endpoint: str, duration_ms: float, success: bool):
        """Record request metrics"""
        self.request_count[endpoint] += 1
        self.response_times.append(duration_ms)
        
        if not success:
            self.error_count += 1
            
        # Keep only last 1000 response times
        if len(self.response_times) > 1000:
            self.response_times = self.response_times[-1000:]
    
    def get_metrics(self) -> dict:
        """Get current metrics"""
        if not self.response_times:
            avg_response_time = 0
        else:
            avg_response_time = sum(self.response_times) / len(self.response_times)
            
        total_requests = sum(self.request_count.values())
        error_rate = self.error_count / total_requests if total_requests > 0 else 0
        
        return {
            "total_requests": total_requests,
            "requests_by_endpoint": dict(self.request_count),
            "average_response_time_ms": avg_response_time,
            "error_rate": error_rate,
            "error_count": self.error_count
        }

# Global metrics instance
metrics = SimpleMetrics()
```

## 📈 Usage Analytics

### Privacy-Preserving Analytics

```python
# app/models/analytics.py
import time
from pydantic import BaseModel
from typing import Optional
import hashlib

class TranslationAnalytics(BaseModel):
    """Anonymous translation analytics"""
    session_id: str  # Client-generated UUID
    method: str      # Translation method used
    confidence: float  # Translation confidence
    duration_ms: float  # Processing time
    cache_hit: bool = False
    success: bool = True
    
    def anonymize(self) -> dict:
        """Return anonymized version for logging"""
        return {
            "timestamp": time.time(),
            "method": self.method,
            "confidence": round(self.confidence, 2),
            "duration_ms": round(self.duration_ms, 1),
            "cache_hit": self.cache_hit,
            "success": self.success,
            # Session ID is already anonymous UUID from client
            "session_hash": hashlib.sha256(self.session_id.encode()).hexdigest()[:8]
        }

class FeedbackSubmission(BaseModel):
    """User feedback submission"""
    input: str
    expected: str
    actual: str
    rating: int  # 1-5 stars
    comments: Optional[str] = None
    
    def sanitize(self) -> dict:
        """Return sanitized version for storage"""
        return {
            "timestamp": time.time(),
            "input_length": len(self.input),
            "expected_length": len(self.expected),
            "actual_length": len(self.actual),
            "rating": self.rating,
            "has_comments": bool(self.comments),
            "feedback_id": f"fb_{int(time.time())}"
        }
```

## 🔒 Security

### Basic Security Measures

```python
# app/core/security.py
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer
import time
from collections import defaultdict

class RateLimiter:
    """Simple rate limiting"""
    
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests = defaultdict(list)
    
    async def check_rate_limit(self, request: Request):
        """Check if request is within rate limits"""
        client_ip = request.client.host
        now = time.time()
        minute_ago = now - 60
        
        # Clean old requests
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if req_time > minute_ago
        ]
        
        # Check current count
        if len(self.requests[client_ip]) >= self.requests_per_minute:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later."
            )
        
        # Add current request
        self.requests[client_ip].append(now)

# Input validation
def validate_input(text: str, max_length: int = 500) -> str:
    """Basic input validation and sanitization"""
    if not text or not isinstance(text, str):
        raise ValueError("Invalid input")
    
    # Remove control characters
    cleaned = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
    
    # Limit length
    if len(cleaned) > max_length:
        raise ValueError(f"Input too long (max {max_length} characters)")
    
    return cleaned.strip()

# CORS configuration
CORS_CONFIG = {
    "allow_origins": [
        "http://localhost:3000",
        "https://dhkalign.com",
        "https://www.dhkalign.com"
    ],
    "allow_credentials": True,
    "allow_methods": ["GET", "POST"],
    "allow_headers": ["*"],
}
```

## 📚 API Documentation

The backend automatically generates interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Example Integration

```javascript
// Frontend integration example
const API_BASE = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

// Log translation analytics
async function logTranslation(analyticsData) {
  try {
    await fetch(`${API_BASE}/api/translate/analytics`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(analyticsData)
    });
  } catch (error) {
    console.warn('Analytics logging failed:', error);
    // Fail silently - analytics is optional
  }
}

// Submit feedback
async function submitFeedback(feedbackData) {
  try {
    const response = await fetch(`${API_BASE}/api/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(feedbackData)
    });
    
    if (response.ok) {
      const result = await response.json();
      return result.feedback_id;
    }
  } catch (error) {
    console.error('Feedback submission failed:', error);
    throw error;
  }
}
```

## 📚 Related Docs

- [Security Policy](../docs/SECURITY.md)
- [Privacy Policy](../docs/PRIVACY.md)
- [Frontend README](../frontend/README.md)
- [Project Overview](../README.md)

## 🤝 Contributing

We welcome contributions to improve the backend service! Please see our [CONTRIBUTING.md](../docs/CONTRIBUTING.md) for guidelines.

### Areas for Contribution

- 📊 Enhanced analytics and metrics
- 🔍 Better health monitoring
- 📈 Performance optimizations
- 🧪 Additional test coverage
- 📚 Documentation improvements

## 📄 License

MIT License - see [LICENSE](../LICENSE) file for details.

---

<div align="center">
  <p>Backend documentation for DHK Align</p>
  <p>
    <a href="../README.md">← Back to main README</a> •
    <a href="mailto:info@dhkalign.com">Support</a> •
    <a href="mailto:admin@dhkalign.com?subject=SECURITY">Security</a> •
    <a href="mailto:admin@dhkalign.com">Admin</a>
  </p>
</div>