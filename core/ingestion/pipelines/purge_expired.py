import json
import logging
from pathlib import Path

from ingestion.core.es_repository import get_client, delete_documents_by_ids as es_delete_ids
from ingestion.core.repository import find_expired_documents, delete_documents_by_ids as pg_delete_ids
from ingestion.core.storage import UPLOAD_DIR
from ingestion.pipelines.ingest_folder import _get_pg_conn

logger = logging.getLogger(__name__)


def _delete_kept_file(path: str) -> bool:
    """
    Delete a kept upload file, then its source folder if now empty.

    Only files inside UPLOAD_DIR are ever touched — documents ingested in
    place (e.g. data/samples/) are never temporary, but this guard makes sure.
    Returns True if a file was deleted.
    """
    upload_root = UPLOAD_DIR.resolve()
    file_path = Path(path).resolve()

    if upload_root not in file_path.parents or not file_path.is_file():
        return False

    file_path.unlink()

    # Remove data/uploads/<source>/ once its last file is gone
    folder = file_path.parent
    if folder.parent == upload_root and not any(folder.iterdir()):
        folder.rmdir()

    return True


def purge_expired() -> dict:
    """
    Delete every temporary upload whose retention has passed.

    For each expired document, in order:
    1. Elasticsearch index          (search already ignores it — this frees it)
    2. PostgreSQL row               (chunks cascade)
    3. Kept original file, if any   (data/uploads/<source>/...)

    Idempotent — safe to run on a schedule (see the docka_purge_expired DAG).
    Returns a summary: expired, es_deleted, pg_deleted, files_deleted.
    """
    conn = _get_pg_conn()
    try:
        expired = find_expired_documents(conn)
        doc_ids = [d["doc_id"] for d in expired]

        es_deleted = es_delete_ids(get_client(), doc_ids)
        pg_deleted = pg_delete_ids(conn, doc_ids)
    finally:
        conn.close()

    files_deleted = sum(
        _delete_kept_file(d["path"]) for d in expired if d["file_retained"]
    )

    summary = {
        "expired": len(expired),
        "es_deleted": es_deleted,
        "pg_deleted": pg_deleted,
        "files_deleted": files_deleted,
    }

    logger.info(json.dumps({"event": "purge_expired", **summary}))
    return summary
