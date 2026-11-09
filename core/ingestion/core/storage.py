"""
Upload storage — where retained upload files live on disk.

DocKA lets the user decide, per upload, whether the ORIGINAL files are kept:
- kept     → stored under UPLOAD_DIR/<source>/ (can be re-ingested / re-chunked later)
- not kept → processed from a temporary folder and deleted; only the
             extracted text (chunks in PostgreSQL, index in Elasticsearch) remains

Pure path logic, no I/O except where stated — shared by the UI (saving)
and the remove-source pipeline (deleting).
"""

import os
from pathlib import Path

# Mounted from the host's data/ folder in the ui and Airflow containers
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/data/uploads"))


def source_upload_dir(source: str, upload_root: Path = UPLOAD_DIR) -> Path:
    """
    Return the folder holding retained files for a source tag.

    The source tag is user input and becomes a folder name, so it must not
    escape upload_root (e.g. "../../etc", "/abs/path", or empty).

    Raises:
        ValueError: if the resulting folder is not strictly inside upload_root
    """
    if not source or not source.strip():
        raise ValueError("Source tag must not be empty")

    root = upload_root.resolve()
    target = (root / source.strip()).resolve()

    # Must be a direct child of the upload root: no traversal, no nesting
    if target.parent != root:
        raise ValueError(f"Invalid source tag for storage: {source!r}")

    return target


def stored_path(file_path: Path, root_path: Path, stored_root: Path | None) -> str:
    """
    Path recorded in PostgreSQL for an ingested file.

    - stored_root None → the real file path (files ingested in place)
    - stored_root set  → file_path re-rooted under stored_root, used when the
      file is processed from a temporary folder: the record then shows the
      logical upload location instead of a temp path that no longer exists
    """
    if stored_root is None:
        return str(file_path)
    return str(stored_root / file_path.relative_to(root_path))
