import psycopg2
from pathlib import Path
import uuid

from Ingestion.core.loader import load_file
from Ingestion.core.checksum import file_checksum
from Ingestion.core.repository import document_exists, insert_document

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "docka",
    "user": "docka",
    "password": "docka",
}

def main():
    conn = psycopg2.connect(**DB_CONFIG)

    folder = Path("data/samples/CrystalcloudDoc")

    for file_path in folder.glob("*.pdf"):
        checksum = file_checksum(str(file_path))

        if document_exists(conn, checksum):
            print("[SKIP]", file_path.name)
            continue

        text = load_file(file_path)

        doc = {
            "doc_id": str(uuid.uuid4()),
            "source": "filesystem",
            "path": str(file_path),
            "title": file_path.stem,
            "language": "en",
            "checksum": checksum,
            "content": text,
        }

        insert_document(conn, doc)
        print("[INGESTED]", file_path.name)

    conn.close()

if __name__ == "__main__":
    main()
