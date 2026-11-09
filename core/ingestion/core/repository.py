import psycopg2

# ---------------------------------------------------------------------------
# chunks table — Phase 2
#
# Single definition, used by ensure_chunks_table() for existing databases.
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
            INSERT INTO documents (doc_id, source, path, title, language, checksum)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (checksum) DO NOTHING
            """,
            (
                doc["doc_id"],
                doc["source"],
                doc["path"],
                doc.get("title"),
                doc.get("language"),
                doc["checksum"]
            )
        )
        conn.commit()


def ensure_chunks_table(conn):
    """
    Create the chunks table if it does not exist.
    Idempotent — safe to call on every pipeline run (mirrors ensure_index).
    Lets existing databases gain the table without a volume reset.
    """
    with conn.cursor() as cur:
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
