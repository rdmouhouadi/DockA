from pathlib import Path
from Ingestion.core.loader import load_file
from Ingestion.core.checksum import file_checksum
from Ingestion.core.repository import document_exists, insert_document
import psycopg2
import uuid

def ingest_folder(root_path: Path, source: str):
    conn = psycopg2.connect(
        host="postgres",
        dbname="docka",
        user="docka",
        password="docka"
    )

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
            print(f"[ERROR] {path}: {e}")
            summary["failed"] += 1

    conn.close()
    return summary
