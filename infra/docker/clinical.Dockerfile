# ============================================================================
# DocKA Clinical — Vertical Image
#
# Extends the core base image with clinical-specific capabilities:
# - Medical NLP (entity extraction: diagnoses, medications, labs, allergies)
# - OCR for scanned clinical documents
# - Neo4j Python driver (patient timeline graph)
#
# Build (from repo root — build core first):
#   docker build -f infra/docker/core.Dockerfile     -t docka-core:latest .
#   docker build -f infra/docker/clinical.Dockerfile -t docka-clinical:latest .
#
# Status: STUB — dependencies and entrypoint are added in Month 2.
# ============================================================================

# ---------------------------------------------------------------------------
# Base image — DocKA Core
#
# CORE_IMAGE is overridable so CI or compose can pass a tagged core build:
#   --build-arg CORE_IMAGE=docka-core:0.2.0
# ---------------------------------------------------------------------------
ARG CORE_IMAGE=docka-core:latest
FROM ${CORE_IMAGE}

# ---------------------------------------------------------------------------
# Clinical Python dependencies
#
# TODO (Month 2): add verticals/clinical/requirements.txt with pinned
# versions (neo4j driver, medical NLP model, OCR bindings), then:
#   COPY verticals/clinical/requirements.txt /tmp/clinical-requirements.txt
#   RUN pip install --no-cache-dir -r /tmp/clinical-requirements.txt
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Clinical vertical code
#
# Lives next to core packages so it can import `ingestion.*` / `app.*`.
# ---------------------------------------------------------------------------
COPY verticals/clinical ./verticals/clinical

# TODO (Month 2): define the clinical entrypoint (API or Streamlit UI)
