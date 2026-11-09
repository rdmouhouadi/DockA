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

    On an existing index, NEW fields of the mapping are added in place
    (Elasticsearch allows adding fields, not changing existing ones).
    To change an existing field's type, rebuild the index (reindex).
    Pass mapping_path=None to fall back to Elasticsearch dynamic mapping.
    """
    mapping = {}
    if mapping_path:
        with open(mapping_path, encoding="utf-8") as f:
            mapping = json.load(f)

    if client.indices.exists(index=INDEX_NAME):
        properties = mapping.get("mappings", {}).get("properties")
        if properties:
            client.indices.put_mapping(index=INDEX_NAME, properties=properties)
        logger.info(f"Index '{INDEX_NAME}' already exists — mapping fields synced")
        return

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
            "created_at": doc.get("created_at"),
            # Temporary uploads — search ignores the document once this passes
            "expires_at": _iso(doc.get("expires_at"))
        }
    )


def _iso(value):
    """datetime → ISO 8601 string for Elasticsearch (None stays None)."""
    return value.isoformat() if value is not None else None


def update_expiry(client: Elasticsearch, doc_id: str, expires_at):
    """Sync an already-indexed document's expires_at with PostgreSQL."""
    client.update(index=INDEX_NAME, id=doc_id, doc={"expires_at": _iso(expires_at)})


def delete_documents_by_ids(client: Elasticsearch, doc_ids: list[str]) -> int:
    """Remove documents from the index by doc_id. Returns the number deleted."""
    if not doc_ids or not client.indices.exists(index=INDEX_NAME):
        return 0
    resp = client.delete_by_query(
        index=INDEX_NAME,
        query={"terms": {"doc_id": doc_ids}},
        refresh=True,
    )
    return resp["deleted"]

def delete_documents_by_source(client: Elasticsearch, source: str) -> int:
    """
    Remove every indexed document of a source tag.
    refresh=True so the removal is visible to the very next search.

    Returns the number of documents deleted (0 if the index does not exist).
    """
    if not client.indices.exists(index=INDEX_NAME):
        return 0

    resp = client.delete_by_query(
        index=INDEX_NAME,
        query={"term": {"source": source}},
        refresh=True,
    )
    return resp["deleted"]
