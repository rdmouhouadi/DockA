# ============================================================================
# DocKA Utility — Vertical Image
#
# Extends the core base image with smart-metering-specific capabilities:
# - Utility document extractors (meter datasheets, asset records)
# - Asset history ingestion pipelines
#
# Build (from repo root — build core first):
#   docker build -f infra/docker/core.Dockerfile    -t docka-core:latest .
#   docker build -f infra/docker/utility.Dockerfile -t docka-utility:latest .
#
# Status: STUB — scheduled after the job search.
# ============================================================================

# ---------------------------------------------------------------------------
# Base image — DocKA Core (overridable, see clinical.Dockerfile)
# ---------------------------------------------------------------------------
ARG CORE_IMAGE=docka-core:latest
FROM ${CORE_IMAGE}

# ---------------------------------------------------------------------------
# Utility Python dependencies
#
# TODO: add verticals/utility/requirements.txt with pinned versions, then:
#   COPY verticals/utility/requirements.txt /tmp/utility-requirements.txt
#   RUN pip install --no-cache-dir -r /tmp/utility-requirements.txt
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Utility vertical code
# ---------------------------------------------------------------------------
COPY verticals/utility ./verticals/utility

# TODO: define the utility entrypoint (API or Streamlit UI)
