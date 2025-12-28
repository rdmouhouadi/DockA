import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import psycopg2
from pathlib import Path
from Ingestion.core.loader import scan_directory
from Ingestion.core.checksum import file_checksum
from Ingestion.core.repository import document_exists, insert_document
import uuid

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "docka",
    "user": "docka",
    "password": "docka",
}

def main():
    conn = psycopg2.connect(**DB_CONFIG)

    base_path = "data/raw"

    for file_path in scan_directory(base_path):
        checksum = file_checksum(str(file_path))

        if document_exists(conn, checksum):
            print(f"[SKIP] {file_path.name}")
            continue

        doc = {
            "doc_id": str(uuid.uuid4()),
            "source": "filesystem",
            "path": str(file_path),
            "title": file_path.stem,
            "language": "en",
            "checksum": checksum,
        }

        insert_document(conn, doc)
        print(f"[INGESTED] {file_path.name}")

    conn.close()

if __name__ == "__main__":
    main()
