# syntax=docker/dockerfile:1
FROM python:3.11-slim

# Runtime hygiene
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PATH="/home/appuser/.local/bin:$PATH" \
    PORT=8080 \
    WEB_CONCURRENCY=2 \
    PYTHONPATH="/app:/app/backend"

# System deps kept minimal; add build deps only if needed
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first for layer caching
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# Copy application code
COPY . /app

# Create non-root user with stable UID/GID and data dir; ensure write perms for /data (Fly volume)
RUN useradd -u 1000 -ms /bin/bash appuser && mkdir -p /data && chown -R appuser:appuser /app /data
USER appuser

EXPOSE 8080

# Container healthcheck – requires backend /health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD sh -c "curl -fsS http://127.0.0.1:${PORT:-8080}/health || exit 1"

# Start FastAPI (respect PORT/WEB_CONCURRENCY); enable proxy headers behind Fly
CMD ["uvicorn","main:app","--host","0.0.0.0","--port","8080","--workers","1","--proxy-headers","--forwarded-allow-ips=*","--log-level","debug"]
