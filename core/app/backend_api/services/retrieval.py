import os
import logging
from elasticsearch import Elasticsearch

logger = logging.getLogger(__name__)

ES_HOST = os.getenv("ELASTICSEARCH_HOST", "http://elasticsearch:9200")
INDEX_NAME = "docka_documents"


def get_es_client() -> Elasticsearch:
    return Elasticsearch(ES_HOST)


def search_documents(query: str, size: int = 10) -> dict:
    """
    Execute a BM25 full-text search against the Elasticsearch index.

    Searches across title and content fields.
    Returns ranked results with highlighted snippets.

    Args:
        query: The search query string
        size:  Maximum number of results to return

    Returns:
        dict with keys: query, total, results
    """
    client = get_es_client()

    es_query = {
        "query": {
            "multi_match": {
                "query": query,
                "fields": [
                    "title^3",    # Title matches weighted 3x higher than content
                    "content"
                ],
                "type": "best_fields",
                "fuzziness": "AUTO"  # Tolerates minor typos
            }
        },
        "highlight": {
            "fields": {
                "content": {
                    "fragment_size": 200,       # Characters per snippet fragment
                    "number_of_fragments": 2,   # Max fragments per document
                    "pre_tags": ["<em>"],        # Wrap matched terms in <em>
                    "post_tags": ["</em>"]
                },
                "title": {
                    "number_of_fragments": 0    # Return full title with highlight
                }
            }
        },
        "_source": ["doc_id", "title", "source", "path", "language"],
        "size": size
    }

    response = client.search(index=INDEX_NAME, body=es_query)

    hits = response["hits"]["hits"]
    total = response["hits"]["total"]["value"]

    results = []
    for hit in hits:
        source = hit["_source"]
        highlight = hit.get("highlight", {})

        # Extract snippet from highlighted content fragments
        # Fall back to empty string if no highlight available
        content_fragments = highlight.get("content", [])
        snippet = " ... ".join(content_fragments) if content_fragments else ""

        results.append({
            "doc_id": source.get("doc_id"),
            "title": source.get("title"),
            "source": source.get("source"),
            "path": source.get("path"),
            "language": source.get("language"),
            "score": round(hit["_score"], 4),
            "snippet": snippet
        })

    logger.info({
        "event": "search_executed",
        "query": query,
        "total": total,
        "returned": len(results)
    })

    return {
        "query": query,
        "total": total,
        "results": results
    }