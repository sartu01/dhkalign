# syntax=docker/dockerfile:1
FROM python:3.11-slim

# Runtime hygiene
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PATH="/home/appuser/.local/bin:$PATH" \
    PORT=8080 \
    WEB_CONCURRENCY=2

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

# Create non-root user and data dir; ensure write perms for /data (Fly volume)
RUN useradd -ms /bin/bash appuser && mkdir -p /data && chown -R appuser:appuser /app /data
USER appuser

EXPOSE 8080

# Start FastAPI (respect PORT/WEB_CONCURRENCY); use uvicorn workers for concurrency
CMD ["sh", "-lc", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080} --workers ${WEB_CONCURRENCY:-2}"]
