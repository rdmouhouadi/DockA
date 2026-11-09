import psycopg2

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
