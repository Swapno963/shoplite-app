# =========================
# Builder Stage
# =========================
FROM python:3.12-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .

RUN pip install \
    --no-cache-dir \
    --prefix=/install \
    -r requirements.txt


# =========================
# Runtime Stage
# =========================
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV SERVICE_NAME=order-worker

# Copy installed dependencies
COPY --from=builder /install /usr/local

# Copy application code
COPY . .

# Create non-root user
RUN addgroup --system app && \
    adduser --system --ingroup app app && \
    chown -R app:app /app

USER app

EXPOSE 8080

# Health check against metrics/health endpoint
HEALTHCHECK --interval=30s \
            --timeout=5s \
            --start-period=30s \
            --retries=3 \
    CMD python -c "\
import urllib.request; \
urllib.request.urlopen('http://localhost:8080/metrics')" \
|| exit 1

CMD ["python", "worker.py"]