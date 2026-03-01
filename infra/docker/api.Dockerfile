# ============================================================================
# DocKA — FastAPI Service Dockerfile
#
# This container runs the Retrieval API for DocKA.
# Responsibilities:
# - Expose /search endpoint
# - Talk to Elasticsearch (retrieval)
# - Talk to PostgreSQL (metadata)
#
# This Dockerfile is intentionally simple and explicit.
# ============================================================================

# ---------------------------------------------------------------------------
# Base image
#
# We use an official Python image for clarity and reproducibility.
# Slim variant keeps the image lightweight.
# ---------------------------------------------------------------------------
FROM python:3.11-slim

# ---------------------------------------------------------------------------
# Environment configuration
#
# - Prevent Python from writing .pyc files
# - Ensure logs are flushed immediately
# ---------------------------------------------------------------------------
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# ---------------------------------------------------------------------------
# Working directory inside the container
# ---------------------------------------------------------------------------
WORKDIR /app

# ---------------------------------------------------------------------------
# System dependencies
#
# - build-essential: required for some Python packages
# - curl: useful for debugging / health checks
# ---------------------------------------------------------------------------
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# Python dependencies
#
# requirements.txt should contain:
# - fastapi
# - uvicorn
# - psycopg2-binary
# - elasticsearch
#
# Copying this first allows Docker layer caching.
# ---------------------------------------------------------------------------
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# ---------------------------------------------------------------------------
# Application code
#
# We copy only what the API needs:
# - app/api
# - app/common
#
# This keeps the image clean and focused.
# ---------------------------------------------------------------------------
COPY app/backend_api ./app/backend_api

# ---------------------------------------------------------------------------
# Expose port
#
# FastAPI will listen on port 8000.
# ---------------------------------------------------------------------------
EXPOSE 8000

# ---------------------------------------------------------------------------
# Container entrypoint
#
# Uvicorn runs the FastAPI app.
# In production, this could be replaced by Gunicorn + Uvicorn workers.
# ---------------------------------------------------------------------------
CMD ["uvicorn", "app.backend_api.api_main:app", "--host", "0.0.0.0", "--port", "8000"]
