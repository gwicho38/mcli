# Multi-stage Dockerfile for ML System
FROM python:3.11-slim as builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:${PATH}"

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml .
COPY src/ src/

# Create virtual environment and install dependencies
RUN uv venv && \
    . .venv/bin/activate && \
    uv pip install -e ".[ml,prod]"

# Production stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libgomp1 \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 mluser && \
    mkdir -p /app /data /models && \
    chown -R mluser:mluser /app /data /models

# Copy virtual environment from builder
COPY --from=builder --chown=mluser:mluser /app/.venv /app/.venv
COPY --from=builder --chown=mluser:mluser /app/src /app/src

# Copy additional files
COPY --chown=mluser:mluser alembic.ini /app/
COPY --chown=mluser:mluser scripts/entrypoint.sh /app/

# Set environment variables
ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONPATH="/app/src:${PYTHONPATH}" \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=production \
    DATA_DIR=/data \
    MODEL_DIR=/models

# Switch to non-root user
USER mluser
WORKDIR /app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import mcli.ml; print('OK')" || exit 1

# Expose ports
EXPOSE 8000 9090

# Entry point
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["serve"]