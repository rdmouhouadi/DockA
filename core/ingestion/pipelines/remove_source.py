import json
import logging
import shutil

from ingestion.core.es_repository import get_client, delete_documents_by_source as es_delete_source
from ingestion.core.repository import delete_documents_by_source as pg_delete_source
from ingestion.core.storage import source_upload_dir
from ingestion.pipelines.ingest_folder import _get_pg_conn

logger = logging.getLogger(__name__)


def remove_source(source: str) -> dict:
    """
    Make a source tag no longer searchable — "you decide what's searchable".

    Removes, in order:
    1. Its documents from the Elasticsearch index  (no longer searchable)
    2. Its documents from PostgreSQL               (chunks cascade)
    3. Its kept upload files, if any               (data/uploads/<source>/)

    Search is cleared first: if a later step fails, nothing stays searchable,
    and re-running remove_source finishes the job (every step is idempotent).

    Files outside the upload folder (e.g. data/samples/ used by the Airflow
    DAG) are never deleted — the next scheduled run would ingest them again.

    Returns a summary: es_deleted, pg_deleted, files_deleted.
    """
    es_deleted = es_delete_source(get_client(), source)

    conn = _get_pg_conn()
    try:
        pg_deleted = pg_delete_source(conn, source)
    finally:
        conn.close()

    # Retained upload files — only inside the upload root
    files_deleted = False
    try:
        upload_dir = source_upload_dir(source)
    except ValueError:
        # Tag cannot map to an upload folder, so no files were ever kept for it
        upload_dir = None

    if upload_dir is not None and upload_dir.is_dir():
        shutil.rmtree(upload_dir)
        files_deleted = True

    summary = {
        "es_deleted": es_deleted,
        "pg_deleted": pg_deleted,
        "files_deleted": files_deleted,
    }

    logger.info(json.dumps({
        "event": "source_removed",
        "source": source,
        **summary
    }))

    return summary
