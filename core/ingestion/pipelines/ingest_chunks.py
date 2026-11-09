import logging
import json
from ingestion.core.chunker import chunk_text
from ingestion.core.tokenizer import token_offsets
from ingestion.core.repository import chunks_exist, insert_chunks

logger = logging.getLogger(__name__)


def ingest_chunks_postgres(conn, doc: dict) -> int:
    """
    Chunk a normalized document and persist the chunks to PostgreSQL.

    Must run after the document itself is in PostgreSQL (chunks reference
    documents.doc_id).

    Returns the number of chunks inserted, 0 if skipped (already chunked).
    Skipping per document means re-runs also backfill chunks for documents
    ingested before chunking existed.
    Raises on failure.
    """

    if chunks_exist(conn, doc["doc_id"]):
        logger.info(json.dumps({
            "event": "chunks_skipped",
            "doc_id": doc["doc_id"],
            "reason": "already_chunked"
        }))
        return 0

    content = doc.get("content", "")
    chunks = chunk_text(content, token_offsets(content))

    if chunks:
        insert_chunks(conn, doc["doc_id"], chunks)

    logger.info(json.dumps({
        "event": "chunks_inserted",
        "doc_id": doc["doc_id"],
        "chunks": len(chunks)
    }))

    return len(chunks)
