from pathlib import Path
import uuid

import psycopg2

from Ingestion.core.loader import load_file
from Ingestion.core.checksum import file_checksum
from Ingestion.core.repository import document_exists, insert_document


def ingest_folder(root: Path, recursive: bool = True) -> dict:
    """
    Ingest all supported documents from a folder tree.

    Args:
        root (Path): Root directory containing documents.
        recursive (bool): Whether to traverse subfolders.

    Returns:
        dict: Ingestion summary statistics.
    """
    if not root.exists() or not root.is_dir():
        raise ValueError(f"Invalid folder: {root}")

    # --- DB connection (infrastructure concern, kept thin here) ---
    conn = psycopg2.connect(
        host="localhost",
        dbname="docka",
        user="docka",
        password="docka",
        port=5432,
    )

    stats = {
        "ingested": 0,
        "skipped": 0,
        "failed": 0,
    }

    files = root.rglob("*") if recursive else root.iterdir()

    for file in files:
        if not file.is_file():
            continue

        try:
            checksum = file_checksum(str(file))

            if document_exists(conn, checksum):
                stats["skipped"] += 1
                continue

            raw_text = load_file(file)

            # Build document payload (minimal for now)
            doc = {
                "doc_id": str(uuid.uuid4()),
                "source": "filesystem",
                "path": str(file),
                "title": file.stem,
                "language": None,
                "checksum": checksum,
                # content not stored yet (by design)
            }

            insert_document(conn, doc)
            stats["ingested"] += 1

        except Exception as e:
            stats["failed"] += 1
            print(f"[FAILED] {file}: {e}")

    conn.close()
    return stats
