# Multi-stage Dockerfile for ML System

# Stage 1: Base image with Python dependencies
FROM python:3.10-slim as base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: API Server
FROM base as api-server

WORKDIR /app

# Copy source code
COPY src/mcli /app/mcli

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000 9090

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run API server
CMD ["python", "-m", "uvicorn", "mcli.ml.mlops.model_serving:app", "--host", "0.0.0.0", "--port", "8000"]

# Stage 3: Training image
FROM base as training

WORKDIR /app

# Install additional dependencies for training
RUN pip install --no-cache-dir \
    torch==2.0.1 \
    torchvision==0.15.2 \
    pytorch-lightning==2.0.6

# Copy source code
COPY src/mcli /app/mcli

# Set Python path
ENV PYTHONPATH=/app

# Run training pipeline
CMD ["python", "-m", "mcli.ml.mlops.pipeline_orchestrator", "--mode", "train"]

# Stage 4: Data Ingestion
FROM base as ingestion

WORKDIR /app

# Install additional dependencies for data ingestion
RUN pip install --no-cache-dir \
    kafka-python \
    websockets \
    aiohttp

# Copy source code
COPY src/mcli /app/mcli

ENV PYTHONPATH=/app

# Run ingestion pipeline
CMD ["python", "-m", "mcli.ml.data_ingestion.data_pipeline", "--mode", "batch"]

# Stage 5: Backtesting
FROM base as backtesting

WORKDIR /app

# Copy source code
COPY src/mcli /app/mcli

ENV PYTHONPATH=/app

# Run backtesting engine
CMD ["python", "-m", "mcli.ml.backtesting.backtest_engine"]

# Stage 6: MLflow Server
FROM python:3.10-slim as mlflow

WORKDIR /mlflow

# Install MLflow and dependencies
RUN pip install --no-cache-dir \
    mlflow==2.8.0 \
    boto3 \
    psycopg2-binary

EXPOSE 5000

# Run MLflow server
CMD ["mlflow", "server", "--host", "0.0.0.0", "--port", "5000"]