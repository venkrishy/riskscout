# syntax=docker/dockerfile:1
# ---------------------------------------------------------------------------
# Stage 1: Builder — install dependencies
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /build

RUN pip install uv

COPY pyproject.toml .
COPY src/ src/

RUN uv pip install --system --no-cache-dir -e .

# ---------------------------------------------------------------------------
# Stage 2: Runtime — minimal production image
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

# Non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source
COPY src/ src/

# Set ownership
RUN chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

EXPOSE 8000

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

CMD ["python", "-m", "uvicorn", "riskscout.api.main:app", \
     "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
