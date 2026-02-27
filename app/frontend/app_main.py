"""
DocKA — Streamlit Frontend

Provides:
- BM25 keyword search over indexed documents
- File/folder upload with source tagging
- Ingested sources overview in sidebar

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
# Makes DocKA packages importable when running outside Docker
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.abspath("."))

from Ingestion.pipelines.ingest_folder import ingest_folder

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
API_BASE_URL = os.getenv("API_BASE_URL", "http://api:8000")
UPLOAD_DIR = Path("/data/uploads")
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


def get_ingested_sources() -> list[dict]:
    """
    Fetch distinct source tags and document counts from PostgreSQL.
    Used to populate the sidebar sources list.
    """
    try:
        conn = get_pg_conn()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT source, COUNT(*) as doc_count
                FROM documents
                GROUP BY source
                ORDER BY source
            """)
            rows = cur.fetchall()
        conn.close()
        return [{"source": row[0], "count": row[1]} for row in rows]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Sidebar — Ingested Sources + System Status
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("📂 Ingested Sources")

    sources = get_ingested_sources()

    if not sources:
        st.caption("No sources ingested yet.")
    else:
        for s in sources:
            st.markdown(f"• **{s['source']}** ({s['count']} docs)")

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

            # Copy staged files to permanent upload directory
            dest_dir = UPLOAD_DIR / final_source
            dest_dir.mkdir(parents=True, exist_ok=True)

            for file in staging_path.rglob("*"):
                if file.is_file() and file.suffix.lower() in SUPPORTED_EXTENSIONS:
                    shutil.copy2(file, dest_dir / file.name)

            # Run ingestion pipeline
            with st.spinner(f"Ingesting documents into source `{final_source}`..."):
                try:
                    summary = ingest_folder(
                        root_path=dest_dir,
                        source=final_source
                    )

                    st.success(
                        f"✅ Ingestion complete for source `{final_source}`"
                    )
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Ingested", summary["ingested"])
                    col2.metric("Skipped", summary["skipped"])
                    col3.metric("Failed", summary["failed"])

                    # Prompt user to refresh sidebar
                    st.info(
                        "Sources updated. "
                        "Refresh the page to see the new source in the sidebar."
                    )

                except Exception as e:
                    st.error(f"Ingestion failed: {e}")