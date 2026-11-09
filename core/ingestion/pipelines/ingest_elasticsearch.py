import logging
import json
from ingestion.core.es_repository import document_exists_in_index, index_document, update_expiry

logger = logging.getLogger(__name__)


def ingest_document_elasticsearch(es_client, doc: dict) -> bool:
    """
    Index a normalized document into Elasticsearch.

    Returns True if indexed, False if skipped (already exists).
    Raises on failure.
    """

    if document_exists_in_index(es_client, doc["checksum"]):
        # Keep the index's expiry in line with PostgreSQL (a re-upload may
        # have extended it) so search filtering stays correct
        update_expiry(es_client, doc["doc_id"], doc.get("expires_at"))

        logger.info(json.dumps({
            "event": "es_skipped",
            "doc_id": doc["doc_id"],
            "reason": "checksum_exists"
        }))
        return False

    index_document(es_client, doc)

    logger.info(json.dumps({
        "event": "es_indexed",
        "doc_id": doc["doc_id"],
        "path": doc["path"]
    }))

    return True