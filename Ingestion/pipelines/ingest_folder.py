import os
import uuid
import logging
import json
import time
from pathlib import Path

import psycopg2

from Ingestion.core.loader import load_file
from Ingestion.core.checksum import file_checksum
from Ingestion.core.es_repository import get_client, ensure_index
from Ingestion.core.normalizer import normalize_text
from Ingestion.pipelines.ingest_postgres import ingest_document_postgres
from Ingestion.pipelines.ingest_elasticsearch import ingest_document_elasticsearch

logger = logging.getLogger(__name__)


def _get_pg_conn():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        dbname=os.getenv("POSTGRES_DB", "docka_app"),
        user=os.getenv("POSTGRES_USER", "docka"),
        password=os.getenv("POSTGRES_PASSWORD", "docka")
    )


def ingest_folder(root_path: Path, source: str) -> dict:
    """
    Ingest all supported documents from a folder.

    For each document:
    1. Compute checksum
    2. Extract text content
    3. Persist metadata to PostgreSQL
    4. Index content to Elasticsearch

    Both stores are updated idempotently — safe to re-run.
    PostgreSQL is the source of truth for metadata.
    Elasticsearch is the search index.
    """
    start_time = time.time()

    # --- Connections ---------------------------------------------------------
    conn = _get_pg_conn()
    es_client = get_client()
    ensure_index(es_client)

    # --- Ingestion loop ------------------------------------------------------
    summary = {
        "ingested": 0,
        "skipped": 0,
        "failed": 0
    }

    for path in root_path.rglob("*"):
        if not path.is_file():
            continue

        try:
            checksum = file_checksum(str(path))
            raw_content = load_file(path)
            content = normalize_text(raw_content)

            doc = {
                "doc_id": str(uuid.uuid4()),
                "source": source,
                "path": str(path),
                "title": path.stem,
                "language": None,
                "content": content,
                "checksum": checksum,
            }

            pg_inserted = ingest_document_postgres(conn, doc)
            es_indexed = ingest_document_elasticsearch(es_client, doc)

            if pg_inserted or es_indexed:
                summary["ingested"] += 1
            else:
                summary["skipped"] += 1

        except Exception as e:
            logger.error(json.dumps({
                "event": "ingestion_failed",
                "path": str(path),
                "error": str(e)
            }))
            summary["failed"] += 1

    # --- Cleanup -------------------------------------------------------------
    conn.close()

    duration = round(time.time() - start_time, 2)

    logger.info(json.dumps({
        "event": "ingestion_summary",
        "source": source,
        "summary": summary,
        "duration_seconds": duration
    }))

    return summary