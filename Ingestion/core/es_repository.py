import os
import logging
from elasticsearch import Elasticsearch

logger = logging.getLogger(__name__)

ES_HOST = os.getenv("ELASTICSEARCH_HOST", "http://elasticsearch:9200")
INDEX_NAME = "docka_documents"


def get_client() -> Elasticsearch:
    return Elasticsearch(ES_HOST)


def ensure_index(client: Elasticsearch, mapping_path: str = None):
    """
    Create the index with mapping if it does not exist.
    Idempotent — safe to call on every pipeline run.
    """
    if client.indices.exists(index=INDEX_NAME):
        logger.info(f"Index '{INDEX_NAME}' already exists")
        return

    mapping = {}
    if mapping_path:
        import json
        with open(mapping_path) as f:
            mapping = json.load(f)

    client.indices.create(index=INDEX_NAME, body=mapping)
    logger.info(f"Index '{INDEX_NAME}' created")


def document_exists_in_index(client: Elasticsearch, checksum: str) -> bool:
    """Check if a document with this checksum is already indexed."""
    resp = client.search(
        index=INDEX_NAME,
        body={
            "query": {
                "term": {"checksum": checksum}
            },
            "_source": False,
            "size": 1
        }
    )
    return resp["hits"]["total"]["value"] > 0


def index_document(client: Elasticsearch, doc: dict):
    """
    Index a normalized document.
    Uses doc_id as the Elasticsearch document ID for idempotency.
    """
    client.index(
        index=INDEX_NAME,
        id=doc["doc_id"],
        document={
            "doc_id": doc["doc_id"],
            "source": doc.get("source"),
            "path": doc.get("path"),
            "title": doc.get("title"),
            "content": doc.get("content", ""),
            "language": doc.get("language"),
            "checksum": doc.get("checksum"),
            "created_at": doc.get("created_at")
        }
    )