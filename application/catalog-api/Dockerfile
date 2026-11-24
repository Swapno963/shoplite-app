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
ENV SERVICE_NAME=catalog-api

# Install runtime dependencies from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY . .

RUN chmod +x entrypoint.sh

# Create non-root user
RUN addgroup --system app && \
    adduser --system --ingroup app app && \
    chown -R app:app /app

USER app

EXPOSE 8000

# Container health check
HEALTHCHECK --interval=30s \
            --timeout=5s \
            --start-period=30s \
            --retries=3 \
    CMD python -c "\
import urllib.request; \
urllib.request.urlopen('http://localhost:8000/health')" \
|| exit 1

CMD ["./entrypoint.sh"]
