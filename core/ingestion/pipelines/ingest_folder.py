import os
import uuid
import logging
import json
import time
from pathlib import Path

import psycopg2

from ingestion.core.loader import load_file
from ingestion.core.checksum import file_checksum
from ingestion.core.es_repository import get_client, ensure_index
from ingestion.core.normalizer import normalize_text
from ingestion.core.repository import get_doc_id_by_checksum, ensure_schema
from ingestion.core.storage import stored_path
from ingestion.pipelines.ingest_postgres import ingest_document_postgres
from ingestion.pipelines.ingest_chunks import ingest_chunks_postgres
from ingestion.pipelines.ingest_elasticsearch import ingest_document_elasticsearch

from langdetect import detect, LangDetectException

from datetime import datetime, timezone


logger = logging.getLogger(__name__)


def _get_pg_conn():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        dbname=os.getenv("POSTGRES_DB", "docka_app"),
        user=os.getenv("POSTGRES_USER", "docka"),
        password=os.getenv("POSTGRES_PASSWORD", "docka")
    )

def detect_language(text: str) -> str | None:
    try:
        return detect(text)
    except LangDetectException:
        return None

def ingest_folder(
    root_path: Path,
    source: str,
    file_retained: bool = True,
    stored_root: Path | None = None,
    expires_at: datetime | None = None,
) -> dict:
    """
    Ingest all supported documents from a folder.

    Args:
        root_path:     folder to scan (recursively)
        source:        source tag recorded on every document
        file_retained: whether the original files are kept on disk after
                       ingestion — False for uploads the user chose not to keep
        stored_root:   when files are processed from a temporary folder,
                       the logical location recorded as each document's path
                       (see storage.stored_path); None records the real path
        expires_at:    temporary uploads — when the documents must be purged
                       everywhere (see retention.py); None = until removed

    For each document:
    1. Compute checksum
    2. Extract text content
    3. Persist metadata to PostgreSQL
    4. Chunk content and persist chunks to PostgreSQL
    5. Index content to Elasticsearch

    Both stores are updated idempotently — safe to re-run.
    PostgreSQL is the source of truth for metadata.
    Elasticsearch is the search index.
    """
    start_time = time.time()

    # --- Connections ---------------------------------------------------------
    conn = _get_pg_conn()
    ensure_schema(conn)
    es_client = get_client()
    ensure_index(es_client)

    # --- Ingestion loop ------------------------------------------------------
    summary = {
        "ingested": 0,
        "skipped": 0,
        "failed": 0,
        "chunks": 0     # chunks inserted this run (incl. backfill of older documents)
    }

    for path in root_path.rglob("*"):
        if not path.is_file():
            continue

        # Hidden files (.gitkeep, .DS_Store, ...) are never documents
        if path.name.startswith("."):
            continue

        try:
            checksum = file_checksum(str(path))
            raw_content = load_file(path)
            content = normalize_text(raw_content)

            # Reuse the doc_id of already-ingested content so every store
            # (PostgreSQL, chunks, Elasticsearch) shares one stable id
            doc_id = get_doc_id_by_checksum(conn, checksum) or str(uuid.uuid4())

            doc = {
                "doc_id": doc_id,
                "source": source,
                "path": stored_path(path, root_path, stored_root),
                "file_retained": file_retained,
                "expires_at": expires_at,
                "title": path.stem,
                "language": detect_language(content),
                "content": content,
                "checksum": checksum,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            pg_inserted = ingest_document_postgres(conn, doc)
            # After the document row exists — chunks reference documents.doc_id
            chunks_inserted = ingest_chunks_postgres(conn, doc)
            es_indexed = ingest_document_elasticsearch(es_client, doc)

            summary["chunks"] += chunks_inserted

            if pg_inserted or es_indexed or chunks_inserted:
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