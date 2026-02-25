import logging
import json
from Ingestion.core.repository import document_exists, insert_document

logger = logging.getLogger(__name__)


def ingest_document_postgres(conn, doc: dict) -> bool:
    """
    Persist a normalized document to PostgreSQL.

    Returns True if inserted, False if skipped (already exists).
    Raises on failure.
    """

    checksum = doc["checksum"]

    if document_exists(conn, checksum):
        logger.info(json.dumps({
            "event": "postgres_skipped",
            "doc_id": doc["doc_id"],
            "reason": "checksum_exists"
        }))
        return False

    insert_document(conn, doc)

    logger.info(json.dumps({
        "event": "postgres_inserted",
        "doc_id": doc["doc_id"],
        "path": doc["path"]
    }))

    return True