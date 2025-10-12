# DHK Align backend: FastAPI + SQLite (Python 3.11)
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl && \
    rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/backend/requirements.txt
RUN python -m pip install --upgrade pip wheel && \
    pip install -r /app/backend/requirements.txt

COPY backend/ /app/backend/
RUN mkdir -p /app/backend/data

EXPOSE 8090
CMD ["sh","-c","python -m backend.main || uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8090}"]
