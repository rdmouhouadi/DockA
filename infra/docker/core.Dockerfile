# ============================================================================
# DocKA — Core Base Image
#
# Shared foundation for every vertical image (clinical, utility, ...).
# Contains:
# - Python runtime + core requirements
# - core/ingestion  → importable as `ingestion.*`
# - core/app        → importable as `app.*`
#
# Build (from repo root):
#   docker build -f infra/docker/core.Dockerfile -t docka-core:latest .
#
# This image has no CMD on purpose — it is a base layer. Verticals extend it
# with `FROM docka-core` and define their own entrypoint.
# (The existing api/ui/airflow images are unchanged and still built directly.)
# ============================================================================

# ---------------------------------------------------------------------------
# Base image — same Python version as api/ui images for consistency
# ---------------------------------------------------------------------------
FROM python:3.11-slim

# ---------------------------------------------------------------------------
# Environment configuration
#
# - No .pyc files, unbuffered logs
# - PYTHONPATH=/app so `ingestion.*` and `app.*` resolve from any WORKDIR
# ---------------------------------------------------------------------------
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

# ---------------------------------------------------------------------------
# System dependencies
#
# - build-essential: required for some Python packages
# - curl: debugging / health checks
# ---------------------------------------------------------------------------
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# Python dependencies — copied first for Docker layer caching
# ---------------------------------------------------------------------------
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# ---------------------------------------------------------------------------
# Core platform code
#
# Copied to the same container paths used by api/ui images, so imports
# are identical across every DocKA image.
# ---------------------------------------------------------------------------
COPY core/ingestion ./ingestion
COPY core/app ./app
