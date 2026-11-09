import os
import json
import logging
from pathlib import Path

from elasticsearch import Elasticsearch

logger = logging.getLogger(__name__)

ES_HOST = os.getenv("ELASTICSEARCH_HOST", "http://elasticsearch:9200")
INDEX_NAME = "docka_documents"

# Index mapping ships inside the ingestion package (ingestion/mappings/) so it
# is available wherever the package is — Airflow mount and UI image alike.
DEFAULT_MAPPING_PATH = Path(__file__).resolve().parent.parent / "mappings" / "docs_v1.json"


def get_client() -> Elasticsearch:
    return Elasticsearch(ES_HOST)


def ensure_index(client: Elasticsearch, mapping_path: str | Path | None = DEFAULT_MAPPING_PATH):
    """
    Create the index with mapping if it does not exist.
    Idempotent — safe to call on every pipeline run.

    The mapping is only applied at creation time: to apply a changed mapping,
    delete the index and re-run ingestion (the index is disposable —
    PostgreSQL is the source of truth).
    Pass mapping_path=None to fall back to Elasticsearch dynamic mapping.
    """
    if client.indices.exists(index=INDEX_NAME):
        logger.info(f"Index '{INDEX_NAME}' already exists")
        return

    mapping = {}
    if mapping_path:
        with open(mapping_path, encoding="utf-8") as f:
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