import psycopg2

# ---------------------------------------------------------------------------
# documents — columns added after v0.1.0
#
# Applied by ensure_schema() so existing databases upgrade in place.
# infra/postgres/01_init.sql declares the same columns for fresh volumes.
#
# - file_retained: was the ORIGINAL file kept on disk?
#     TRUE  → files ingested in place (samples, Airflow) or uploads the user kept
#     FALSE → uploads processed from a temp folder and deleted; only the
#             extracted text remains (chunks + search index)
#   Default TRUE matches every pre-existing ingestion path except UI uploads,
#   which always pass the value explicitly.
# ---------------------------------------------------------------------------
DOCUMENTS_MIGRATIONS = """
ALTER TABLE documents ADD COLUMN IF NOT EXISTS file_retained BOOLEAN NOT NULL DEFAULT TRUE;
"""

# ---------------------------------------------------------------------------
# chunks table — Phase 2
#
# Single definition, used by ensure_schema() for existing databases.
# infra/postgres/01_init.sql repeats it for fresh volumes — keep both in sync.
#
# - chunk_id "<doc_id>:<chunk_index>" is deterministic → idempotent inserts
# - start_char / end_char locate the chunk in the document (citations, Phase 3)
# - ON DELETE CASCADE: deleting a document removes its chunks
# ---------------------------------------------------------------------------
CHUNKS_DDL = """
CREATE TABLE IF NOT EXISTS chunks (
    id SERIAL PRIMARY KEY,
    chunk_id TEXT UNIQUE NOT NULL,
    doc_id TEXT NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    start_char INT NOT NULL,
    end_char INT NOT NULL,
    token_count INT NOT NULL,
    created_at TIMESTAMP DEFAULT now(),
    UNIQUE (doc_id, chunk_index)
);
CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id);
"""


def document_exists(conn, checksum: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM documents WHERE checksum = %s",
            (checksum,)
        )
        return cur.fetchone() is not None


def get_doc_id_by_checksum(conn, checksum: str) -> str | None:
    """
    Return the doc_id already stored for this content, or None if new.

    Lets re-runs reuse the original doc_id instead of minting a new UUID,
    so chunks and the Elasticsearch document always reference the
    doc_id that exists in PostgreSQL.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT doc_id FROM documents WHERE checksum = %s",
            (checksum,)
        )
        row = cur.fetchone()
        return row[0] if row else None


def insert_document(conn, doc):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO documents (doc_id, source, path, title, language, checksum, file_retained)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (checksum) DO NOTHING
            """,
            (
                doc["doc_id"],
                doc["source"],
                doc["path"],
                doc.get("title"),
                doc.get("language"),
                doc["checksum"],
                doc.get("file_retained", True)
            )
        )
        conn.commit()


def mark_file_retained(conn, checksum: str, path: str) -> bool:
    """
    Record that the original file is now kept for already-ingested content.

    Covers re-uploading the same document with "keep files" on after a first
    upload without it. Never downgrades: a document whose file is already
    kept is left untouched.

    Returns True if a row was updated.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE documents
            SET file_retained = TRUE, path = %s, updated_at = now()
            WHERE checksum = %s AND NOT file_retained
            """,
            (path, checksum)
        )
        updated = cur.rowcount > 0
    conn.commit()
    return updated


def ensure_schema(conn):
    """
    Bring an existing database up to the current schema.
    Idempotent — safe to call on every pipeline run (mirrors ensure_index).
    Lets existing databases upgrade without a volume reset:
    - new documents columns (DOCUMENTS_MIGRATIONS)
    - chunks table (CHUNKS_DDL)
    """
    with conn.cursor() as cur:
        cur.execute(DOCUMENTS_MIGRATIONS)
        cur.execute(CHUNKS_DDL)
    conn.commit()


def chunks_exist(conn, doc_id: str) -> bool:
    """True if this document has already been chunked."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM chunks WHERE doc_id = %s LIMIT 1",
            (doc_id,)
        )
        return cur.fetchone() is not None


def insert_chunks(conn, doc_id: str, chunks: list[dict]):
    """
    Persist all chunks of one document in a single transaction.
    ON CONFLICT DO NOTHING keeps re-runs idempotent.
    """
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO chunks (chunk_id, doc_id, chunk_index, content,
                                start_char, end_char, token_count)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (chunk_id) DO NOTHING
            """,
            [
                (
                    f"{doc_id}:{c['chunk_index']}",
                    doc_id,
                    c["chunk_index"],
                    c["content"],
                    c["start_char"],
                    c["end_char"],
                    c["token_count"],
                )
                for c in chunks
            ]
        )
    conn.commit()
