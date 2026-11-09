"""
DocKA — Streamlit Frontend

Provides:
- BM25 keyword search over indexed documents
- File/folder upload with source tagging
- Per-upload choices: keep the original files or not (off by default), and
  how long the content stays searchable (temporary by default, or until removed)
- Ingested sources overview in sidebar, with source removal

Upload modes supported:
- Single file (PDF, DOCX, TXT, HTML)
- Multiple files at once
- Zipped folder (.zip)
"""

import os
import sys
import zipfile
import tempfile
import shutil
from pathlib import Path

import streamlit as st
import requests
import psycopg2

# ---------------------------------------------------------------------------
# Path setup
# Makes DocKA packages importable when running outside Docker.
# Resolves the directory that contains `app/` and `ingestion/` from this
# file's location (app/frontend/app_main.py → two levels up):
# - locally : <repo>/core
# - Docker  : /app
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ingestion.pipelines.ingest_folder import ingest_folder
from ingestion.pipelines.remove_source import remove_source
from ingestion.core.repository import ensure_schema
from ingestion.core.storage import UPLOAD_DIR, source_upload_dir
from ingestion.core.retention import (
    TEMPORARY_DURATIONS,
    DEFAULT_TEMPORARY_DURATION,
    expiry_for,
    describe_expiry,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
API_BASE_URL = os.getenv("API_BASE_URL", "http://api:8000")
# UPLOAD_DIR (data/uploads, mounted from the host) is defined in storage.py
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".html", ".txt"}

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="DocKA",
    page_icon="📘",
    layout="wide"
)


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------
def get_pg_conn():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        dbname=os.getenv("POSTGRES_DB", "docka_app"),
        user=os.getenv("POSTGRES_USER", "docka"),
        password=os.getenv("POSTGRES_PASSWORD", "docka")
    )


@st.cache_resource
def upgrade_schema_once():
    """
    Bring the database schema up to date once per UI process.
    The sidebar queries columns (file_retained, expires_at) that older
    databases only gain on upgrade — without this it would silently show
    "No sources" until the first ingestion.
    """
    conn = get_pg_conn()
    try:
        ensure_schema(conn)
    finally:
        conn.close()
    return True


def get_ingested_sources() -> list[dict]:
    """
    Fetch distinct source tags, document counts and file retention from
    PostgreSQL. Used to populate the sidebar sources list.

    - files_kept: True only if the original files of ALL the source's
      documents are kept on disk
    - expires_at: None if any document is kept until removed, otherwise the
      latest expiry among its temporary documents
    """
    try:
        upgrade_schema_once()
        conn = get_pg_conn()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT source,
                       COUNT(*)                     AS doc_count,
                       BOOL_AND(file_retained)      AS files_kept,
                       BOOL_OR(expires_at IS NULL)  AS has_permanent,
                       MAX(expires_at)              AS last_expiry
                FROM documents
                GROUP BY source
                ORDER BY source
            """)
            rows = cur.fetchall()
        conn.close()
        return [
            {
                "source": row[0],
                "count": row[1],
                "files_kept": row[2],
                "expires_at": None if row[3] else row[4],
            }
            for row in rows
        ]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Sidebar — Ingested Sources + System Status
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("📂 Ingested Sources")

    # Confirmation from a source removal on the previous run
    if "removal_message" in st.session_state:
        st.success(st.session_state.pop("removal_message"))

    sources = get_ingested_sources()

    if not sources:
        st.caption("No sources ingested yet.")
    else:
        for s in sources:
            # Show whether DocKA still holds the original files or only text
            files = "🗂️ files kept" if s["files_kept"] else "🔒 text only"
            # ...and how long it stays searchable
            lifetime = ("⏳ " if s["expires_at"] else "♾️ ") + describe_expiry(s["expires_at"])
            st.markdown(f"• **{s['source']}** ({s['count']} docs) · {files} · {lifetime}")

        # --- Remove a source ------------------------------------------------
        # "You decide what's searchable": removing a source deletes it from
        # the search index, PostgreSQL (incl. chunks) and any kept files.
        with st.expander("🗑️ Remove a source"):
            source_to_remove = st.selectbox(
                "Source",
                [s["source"] for s in sources],
                label_visibility="collapsed",
            )
            st.caption(
                "Deletes its documents from search and from the database, "
                "and its kept files in data/uploads/. Folders ingested by Airflow "
                "(e.g. data/samples/) are not deleted and will be re-ingested on the next run."
            )
            confirm_remove = st.checkbox(f"Yes, remove `{source_to_remove}`")

            if st.button("Remove source", disabled=not confirm_remove, type="primary"):
                try:
                    result = remove_source(source_to_remove)
                    # Shown after the rerun (a message rendered now would be lost)
                    st.session_state["removal_message"] = (
                        f"Removed `{source_to_remove}`: "
                        f"{result['pg_deleted']} documents"
                        + (", kept files deleted" if result["files_deleted"] else "")
                    )
                    st.rerun()
                except Exception as e:
                    st.error(f"Removal failed: {e}")

    st.divider()

    st.header("⚙️ System Status")
    if st.button("Check health"):
        try:
            r = requests.get(f"{API_BASE_URL}/health", timeout=3)
            health = r.json()
            st.success("API reachable")
            for service, status in health.items():
                icon = "✅" if status == "ok" else "❌"
                st.write(f"{icon} {service}: {status}")
        except Exception as e:
            st.error(f"API unreachable: {e}")


# ---------------------------------------------------------------------------
# Main — Title
# ---------------------------------------------------------------------------
st.title("📘 DocKA — Document Knowledge Access")
st.caption("Search your knowledge base using keyword search (BM25)")

# ---------------------------------------------------------------------------
# Tabs — Search / Upload
# ---------------------------------------------------------------------------
tab_search, tab_upload = st.tabs(["🔍 Search", "📤 Upload Documents"])


# =============================================================================
# TAB 1 — Search
# =============================================================================
with tab_search:

    col1, col2 = st.columns([5, 1])

    with col1:
        query = st.text_input(
            label="Search query",
            placeholder="e.g. bluetooth alarme compteur...",
            label_visibility="collapsed"
        )

    with col2:
        size = st.selectbox(
            "Results",
            [5, 10, 20],
            index=1,
            label_visibility="collapsed"
        )

    search_clicked = st.button("🔍 Search", use_container_width=False)

    if search_clicked and query.strip():
        try:
            response = requests.get(
                f"{API_BASE_URL}/search",
                params={"q": query, "size": size},
                timeout=5
            )
            data = response.json()

            if response.status_code != 200:
                st.error(f"Search failed: {data.get('detail', 'Unknown error')}")
            else:
                total = data["total"]
                results = data["results"]

                st.markdown(f"**{total} documents found** for `{query}`")
                st.divider()

                if not results:
                    st.info("No results found. Try a different query.")
                else:
                    for r in results:
                        with st.container():
                            col_title, col_score = st.columns([6, 1])

                            with col_title:
                                st.markdown(f"### 📄 {r['title']}")

                            with col_score:
                                st.metric(label="Score", value=round(r["score"], 2))

                            # Language badge
                            lang = r.get("language")
                            lang_badge = f"🌐 `{lang}`" if lang else ""

                            st.caption(
                                f"📁 {r['path']}  |  "
                                f"🏷️ Source: `{r['source']}`  |  "
                                f"{lang_badge}"
                            )

                            # Highlighted snippet
                            snippet = r.get("snippet", "")
                            if snippet:
                                snippet_html = snippet.replace("\n", " ")
                                st.markdown(
                                    f"<div style='background:#1e1e2e;padding:10px;"
                                    f"border-radius:6px;font-size:0.9em;"
                                    f"color:#e0e0e0'>{snippet_html}</div>",
                                    unsafe_allow_html=True
                                )

                            st.divider()

        except Exception as e:
            st.error(f"Could not reach API: {e}")

    elif search_clicked and not query.strip():
        st.warning("Please enter a search query.")


# =============================================================================
# TAB 2 — Upload
# =============================================================================
with tab_upload:

    st.subheader("Upload Documents")
    st.caption(
        "Supported formats: PDF, DOCX, TXT, HTML — "
        "or upload a ZIP file containing multiple documents."
    )

    # --- Source tag input ----------------------------------------------------
    source_tag = st.text_input(
        label="Source tag (optional)",
        placeholder="e.g. healthcare, project_x, my_reports",
        help=(
            "Tag used to identify this batch of documents. "
            "Defaults to the filename if left empty."
        )
    )

    # --- Two explicit storage choices ---------------------------------------
    # Searching requires storing the extracted text (chunks + search index),
    # so the user decides separately:
    # 1. HOW LONG the content is stored and searchable
    #    - Temporary (default): purged everywhere after the chosen duration
    #    - Until I remove it:   stays until the source is removed
    # 2. WHETHER the original files are kept (off by default)
    #    - kept in data/uploads/<source>/ (for the same lifetime) so DocKA
    #      can re-process them later, or deleted right after ingestion
    lifetime_choice = st.radio(
        "Searchable",
        ["Temporary", "Until I remove it"],
        index=0,
        horizontal=True,
        help=(
            "Temporary: the documents, their extracted text and any kept files "
            "are deleted automatically after the chosen duration."
        )
    )

    duration_label = None
    if lifetime_choice == "Temporary":
        duration_label = st.selectbox(
            "Delete after",
            list(TEMPORARY_DURATIONS),
            index=list(TEMPORARY_DURATIONS).index(DEFAULT_TEMPORARY_DURATION),
        )

    keep_files = st.checkbox(
        "Keep a copy of the original files",
        value=False,
        help=(
            "Off: the files are deleted right after their text is extracted. "
            "On: the files are kept in data/uploads/<source>/ so DocKA can re-process them later."
        )
    )

    # Say exactly what will be stored, before anything is uploaded
    stored_for = (
        f"for **{duration_label}**, then deleted automatically"
        if duration_label else "until you remove this source"
    )
    files_note = (
        "Original files are **kept** for the same period."
        if keep_files else "Original files are **not kept**."
    )
    st.info(
        f"DocKA will store the extracted text (needed for search) {stored_for}. {files_note}"
    )

    # --- File uploader -------------------------------------------------------
    uploaded_files = st.file_uploader(
        label="Choose files",
        type=["pdf", "docx", "txt", "html", "zip"],
        accept_multiple_files=True,
        label_visibility="collapsed"
    )

    ingest_clicked = st.button(
        "⚙️ Ingest Documents",
        disabled=not uploaded_files
    )

    if ingest_clicked and uploaded_files:

        # Create a temporary staging directory for this upload batch
        with tempfile.TemporaryDirectory() as staging_dir:
            staging_path = Path(staging_dir)
            saved_files = []

            for uploaded_file in uploaded_files:
                file_path = staging_path / uploaded_file.name

                # Write uploaded file to staging directory
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                # Handle ZIP files — extract contents
                if uploaded_file.name.endswith(".zip"):
                    with zipfile.ZipFile(file_path, "r") as zip_ref:
                        zip_ref.extractall(staging_path)
                    # Remove the zip itself — we only want extracted files
                    file_path.unlink()
                else:
                    saved_files.append(file_path)

            # Determine source tag
            # - If user provided a tag → use it
            # - If single file uploaded → use filename stem
            # - If multiple files → use "upload"
            if source_tag.strip():
                final_source = source_tag.strip()
            elif len(uploaded_files) == 1:
                final_source = Path(uploaded_files[0].name).stem
            else:
                final_source = "upload"

            # Validate the source tag — it becomes a folder name under
            # data/uploads/ (also recorded as the logical path when not kept)
            try:
                dest_dir = source_upload_dir(final_source)
            except ValueError as e:
                st.error(f"Invalid source tag: {e}")
                st.stop()

            # Gather supported files into one flat batch folder
            # (ZIP archives may contain other file types or nested folders)
            batch_dir = staging_path / "_batch"
            batch_dir.mkdir()
            for file in staging_path.rglob("*"):
                if (
                    file.is_file()
                    and batch_dir not in file.parents
                    and file.suffix.lower() in SUPPORTED_EXTENSIONS
                ):
                    shutil.copy2(file, batch_dir / file.name)

            if keep_files:
                # Keep originals: copy to data/uploads/<source>/ and ingest there
                dest_dir.mkdir(parents=True, exist_ok=True)
                for file in batch_dir.iterdir():
                    shutil.copy2(file, dest_dir / file.name)
                ingest_kwargs = {"root_path": dest_dir, "file_retained": True}
            else:
                # Do not keep: ingest straight from the temp folder, which is
                # deleted when this block exits. Recorded paths point to the
                # logical upload location, flagged file_retained = False.
                ingest_kwargs = {
                    "root_path": batch_dir,
                    "file_retained": False,
                    "stored_root": dest_dir,
                }

            # Expiry is computed at ingestion time, not when the page loaded
            ingest_kwargs["expires_at"] = expiry_for(duration_label)

            # Run ingestion pipeline
            with st.spinner(f"Ingesting documents into source `{final_source}`..."):
                try:
                    summary = ingest_folder(source=final_source, **ingest_kwargs)

                    st.success(
                        f"✅ Ingestion complete for source `{final_source}`"
                    )
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Ingested", summary["ingested"])
                    col2.metric("Skipped", summary["skipped"])
                    col3.metric("Failed", summary["failed"])
                    col4.metric("Chunks", summary["chunks"])

                    if keep_files:
                        st.caption(f"🗂️ Original files kept in `data/uploads/{dest_dir.name}/`.")
                    else:
                        st.caption("🔒 Original files were not kept.")

                    if ingest_kwargs["expires_at"]:
                        st.caption(
                            f"⏳ Searchable until {ingest_kwargs['expires_at']:%Y-%m-%d %H:%M} UTC, "
                            "then deleted automatically."
                        )
                    else:
                        st.caption("♾️ Searchable until you remove this source.")

                    # Prompt user to refresh sidebar
                    st.info(
                        "Sources updated. "
                        "Refresh the page to see the new source in the sidebar."
                    )

                except Exception as e:
                    st.error(f"Ingestion failed: {e}")