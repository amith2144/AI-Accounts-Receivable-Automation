# ==============================================================================
# Stage 1: Build virtual environment with uv
# ==============================================================================
FROM python:3.11-slim AS builder

WORKDIR /app

# Install uv binary from official Astral distribution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set uv environment variables for fast containerized builds
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Install build dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency manifests first for maximum Docker layer caching
COPY pyproject.toml uv.lock README.md ./

# Install production dependencies only into .venv
RUN uv sync --frozen --no-dev --no-install-project

# Copy source code and install project
COPY app ./app
RUN uv sync --frozen --no-dev

# ==============================================================================
# Stage 2: Lightweight, hardened production runtime
# ==============================================================================
FROM python:3.11-slim AS runtime

WORKDIR /app

# Install runtime dependencies (curl for healthcheck, libmupdf/tesseract if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create dedicated non-root user and group (Standard 1 & Security Hardening)
RUN groupadd -r -g 10001 appgroup && \
    useradd -r -u 10001 -g appgroup -s /bin/false -d /app appuser

# Copy virtual environment and application code from builder
COPY --from=builder --chown=appuser:appgroup /app/.venv /app/.venv
COPY --chown=appuser:appgroup ./app /app/app
COPY --chown=appuser:appgroup ./alembic /app/alembic
COPY --chown=appuser:appgroup ./alembic.ini /app/alembic.ini

# Expose PATH so python/uvicorn in virtual environment are directly accessible
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

USER appuser

# Port is exposed internally to the Docker bridge network; host binding handled by gateway
EXPOSE 8000

# Production ASGI server running with 4 workers and NO --reload (Standard 3)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--proxy-headers", "--forwarded-allow-ips", "*"]
