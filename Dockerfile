# Multi-stage Dockerfile for MCLI

# Stage 1: Base image with Python dependencies
FROM python:3.11-slim AS base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install from pyproject.toml
COPY pyproject.toml README.md ./
COPY src/ src/
RUN pip install --no-cache-dir .

# Stage 2: API Server
FROM base AS api-server

WORKDIR /app

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run MCLI daemon API
CMD ["python", "-m", "uvicorn", "mcli.workflow.daemon.daemon_api:app", "--host", "0.0.0.0", "--port", "8000"]

# NOTE: The former training / ingestion / backtesting / mlflow stages were
# removed — they referenced the mcli.ml package, which no longer exists (the ML
# code was removed in e4dd441). See docker/ for any ML-specific images.