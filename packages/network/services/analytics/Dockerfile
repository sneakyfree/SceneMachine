# SceneMachine Network - Analytics Service Dockerfile

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ ./shared/
COPY services/analytics/ ./services/analytics/

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8007

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8007/health || exit 1

CMD ["python", "-m", "uvicorn", "services.analytics.main:app", "--host", "0.0.0.0", "--port", "8007"]
