import logging
import json
from Ingestion.core.es_repository import document_exists_in_index, index_document

logger = logging.getLogger(__name__)


def ingest_document_elasticsearch(es_client, doc: dict) -> bool:
    """
    Index a normalized document into Elasticsearch.

    Returns True if indexed, False if skipped (already exists).
    Raises on failure.
    """

    if document_exists_in_index(es_client, doc["checksum"]):
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