import psycopg2

def document_exists(conn, checksum: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM documents WHERE checksum = %s",
            (checksum,)
        )
        return cur.fetchone() is not None


def insert_document(conn, doc):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO documents (doc_id, source, path, title, language, checksum)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (doc_id) DO NOTHING
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
