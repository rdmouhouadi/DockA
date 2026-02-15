from pathlib import Path
from Ingestion.core.loader import load_file
from Ingestion.core.checksum import file_checksum
from Ingestion.core.repository import document_exists, insert_document
import psycopg2
import uuid
import logging
import json
import time


logger = logging.getLogger(__name__)
#logging.basicConfig(level=logging.INFO)


def _ensure_schema(conn):
    """Ensure required database tables exist."""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id SERIAL PRIMARY KEY,
                    doc_id TEXT UNIQUE,
                    source TEXT NOT NULL,
                    path TEXT NOT NULL,
                    title TEXT,
                    language TEXT,
                    checksum TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Optional but recommended indexes
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_checksum
                ON documents(checksum);
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_doc_id
                ON documents(doc_id);
            """)

        conn.commit()

    except Exception as e:
        conn.rollback()
        raise RuntimeError(f"Schema initialization failed: {e}")


def ingest_folder(root_path: Path, source: str):
    start_time = time.time()
    conn = psycopg2.connect(
        host="postgres",
        dbname="docka",
        user="docka",
        password="docka"
    )

    # ✅ Ensure schema before ingestion
    _ensure_schema(conn)

    summary = {"ingested": 0, "skipped": 0, "failed": 0}

    for path in root_path.rglob("*"):
        if not path.is_file():
            continue

        try:
            checksum = file_checksum(str(path))

            if document_exists(conn, checksum):
                summary["skipped"] += 1
                continue

            text = load_file(path)

            doc = {
                "doc_id": str(uuid.uuid4()),
                "source": source,
                "path": str(path),
                "title": path.stem,
                "language": None,
                "checksum": checksum,
            }

            insert_document(conn, doc)
            summary["ingested"] += 1

        except Exception as e:
            #print(f"[ERROR] {path}: {e}")  ---old
            logger.error(json.dumps({
                "event": "ingestion_failed",
                "path": str(path),
                "error": str(e)
            }))
            summary["failed"] += 1

    conn.close()

    duration = round(time.time() - start_time, 2)

    logger.info(json.dumps({
        "event": "ingestion_summary",
        "source": source,
        "summary": summary,
        "duration_seconds": duration
    }))
    
    return summary
