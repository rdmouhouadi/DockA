# ============================================================================
# DocKA — Streamlit UI Dockerfile
#
# This container runs the user-facing UI for DocKA.
# Responsibilities:
# - Accept user queries
# - Call the FastAPI backend
# - Display ranked results and snippets
#
# This UI is intentionally lightweight and replaceable.
# ============================================================================

# ---------------------------------------------------------------------------
# Base image
#
# Python slim image is sufficient for Streamlit.
# ---------------------------------------------------------------------------
FROM python:3.11-slim

# ---------------------------------------------------------------------------
# Environment configuration
# ---------------------------------------------------------------------------
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# ---------------------------------------------------------------------------
# Working directory
# ---------------------------------------------------------------------------
WORKDIR /app

# ---------------------------------------------------------------------------
# System dependencies
#
# - curl: useful for debugging
# ---------------------------------------------------------------------------
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# Python dependencies
#
# requirements.txt should include:
# - streamlit
# - requests
#
# Again, copied early to leverage Docker caching.
# ---------------------------------------------------------------------------
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# ---------------------------------------------------------------------------
# UI application code
#
# Only the UI code + Ingestion package (used for direct pipeline calls
# triggered by user uploads — bypasses Airflow for interactive ingestion)
# ---------------------------------------------------------------------------
COPY app/frontend ./app/frontend
COPY ingestion ./ingestion

# ---------------------------------------------------------------------------
# Expose port
#
# Streamlit default port.
# ---------------------------------------------------------------------------
EXPOSE 8501

# ---------------------------------------------------------------------------
# Container entrypoint
#
# --server.address=0.0.0.0 is mandatory inside Docker.
# ---------------------------------------------------------------------------
CMD ["streamlit", "run", "app/frontend/app_main.py", "--server.address=0.0.0.0", "--server.port=8501"]
