import logging
import json
from ingestion.core.repository import document_exists, insert_document, mark_file_retained, extend_retention

logger = logging.getLogger(__name__)


def ingest_document_postgres(conn, doc: dict) -> bool:
    """
    Persist a normalized document to PostgreSQL.

    Returns True if inserted, False if skipped (already exists).
    Raises on failure.
    """

    checksum = doc["checksum"]

    if document_exists(conn, checksum):
        # Same content seen before: retention can only be extended — the
        # effective expiry is written back to doc for the search index
        doc["expires_at"] = extend_retention(conn, checksum, doc.get("expires_at"))

        # If its original file is kept this time,
        # record that (a previous upload may have been "not kept")
        if doc.get("file_retained", True) and mark_file_retained(conn, checksum, doc["path"]):
            logger.info(json.dumps({
                "event": "postgres_file_retained",
                "doc_id": doc["doc_id"],
                "path": doc["path"]
            }))

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