# 🏗️ DocKA — Architecture

This document describes the technical architecture of DocKA v0.1.0.

---

## Table of Contents

1. [Design Philosophy](#design-philosophy)
2. [System Overview](#system-overview)
3. [Component Breakdown](#component-breakdown)
4. [Data Flow](#data-flow)
5. [Database Design](#database-design)
6. [Ingestion Architecture](#ingestion-architecture)
7. [Search Architecture](#search-architecture)
8. [Infrastructure](#infrastructure)
9. [Key Design Decisions](#key-design-decisions)

---

## Design Philosophy

DocKA is built around three core principles:

**1 — Core First, Infrastructure Later**
All business logic lives in pure Python modules with no dependency on Airflow, Docker, or any framework.
Infrastructure is an adapter. This means the same ingestion code runs in a DAG, a CLI script, a test, or a Streamlit upload handler.

**2 — PostgreSQL is the Source of Truth**
Elasticsearch is a disposable search index. If it is deleted or corrupted, it can be rebuilt
from scratch by re-running the ingestion pipeline. Document metadata and history live in PostgreSQL.

**3 — Idempotency by Design**
Every ingestion operation is safe to re-run. Content-based checksums (SHA-256) prevent
duplicate documents regardless of how many times the pipeline runs.

---

## Repository Layout — Core + Verticals

DocKA is a monorepo organised as **one core platform** with **domain verticals** on top.

| Layer | Location | Contents |
|-------|----------|----------|
| Core | `core/` | Ingestion, search API, UI, tests — domain-agnostic |
| Verticals | `verticals/<name>/` | Domain-specific extractors, pipelines, UI (e.g. `clinical/`, `utility/`) |
| Infrastructure | `infra/` | Dockerfiles (core base image + one per vertical) and compose stacks |

Verticals depend on core, never the other way round. Each vertical image is
built `FROM` the core image, and each vertical compose file `include`s the core stack.

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                          DocKA Platform                              │
│                                                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌────────────────────┐    │
│  │  Data Sources │    │  Ingestion   │    │   Storage Layer    │    │
│  │              │    │  Pipeline    │    │                    │    │
│  │  • Filesystem│───▶│              │───▶│  PostgreSQL        │    │
│  │  • Uploads   │    │  • Extract   │    │  (metadata)        │    │
│  │  • Web APIs  │    │  • Normalize │    │                    │    │
│  │    (Phase 4) │    │  • Checksum  │    │  Elasticsearch     │    │
│  └──────────────┘    │  • Persist   │───▶│  (search index)    │    │
│                       └──────────────┘    └─────────┬──────────┘   │
│                                                      │              │
│  ┌──────────────────────────────────────────────────▼───────────┐  │
│  │                      API Layer (FastAPI)                      │  │
│  │                    GET /search?q=...&size=10                  │  │
│  └──────────────────────────────────────────────────┬───────────┘  │
│                                                      │              │
│  ┌──────────────────────────────────────────────────▼───────────┐  │
│  │                    UI Layer (Streamlit)                       │  │
│  │              Search · Upload · Source Tags                    │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                  Orchestration (Airflow)                       │ │
│  │           Scheduled ingestion · Retries · Monitoring          │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Component Breakdown

### 🔴 Ingestion Core — `core/ingestion/core/`

The heart of DocKA. Pure Python, no framework dependencies.

| Module | Responsibility |
|--------|---------------|
| `loader.py` | Scans directories and dispatches files to the correct extractor |
| `checksum.py` | Computes SHA-256 content hashes for idempotency |
| `normalizer.py` | Cleans extracted text (whitespace, control chars, page numbers) |
| `storage.py` | Upload folder per source (validated) and recorded path for files not kept |
| `retention.py` | Temporary upload durations, expiry computation and merge rule (pure logic) |
| `tokenizer.py` | Embedding model tokenizer — token count and char offsets per token |
| `chunker.py` | Splits text into overlapping, token-bounded chunks (pure logic) |
| `repository.py` | PostgreSQL interactions (documents and chunks: insert, existence checks) |
| `es_repository.py` | Elasticsearch interactions (index creation, document indexing) |

### 🔴 Extractors — `core/ingestion/extractors/`

Each extractor handles exactly one file format and returns clean text.

| Extractor | Format | Library |
|-----------|--------|---------|
| `pdf.py` | PDF documents | pypdf |
| `docx.py` | Word documents | python-docx |
| `html.py` | HTML files | BeautifulSoup4 |
| `txt.py` | Plain text | stdlib only |

**Design rule:** Adding a new format requires only creating a new extractor file
and registering it in `__init__.py`. The pipeline never changes.

### 🟡 Pipelines — `core/ingestion/pipelines/`

Thin orchestration layer. Assembles core modules into reusable workflows.

| Pipeline | Responsibility |
|----------|---------------|
| `ingest_folder.py` | Scans a folder and ingests all supported documents |
| `ingest_postgres.py` | Persists one document to PostgreSQL |
| `ingest_chunks.py` | Chunks one document and persists its chunks to PostgreSQL |
| `remove_source.py` | Removes a source from Elasticsearch, PostgreSQL and kept files |
| `purge_expired.py` | Deletes expired temporary uploads everywhere (run by the `docka_purge_expired` DAG) |
| `ingest_elasticsearch.py` | Indexes one document into Elasticsearch |

Each sub-pipeline handles **one document, one destination**.
`ingest_folder.py` is a coordinator — it calls the others.

### 🔵 Airflow — `core/ingestion/airflow/`

Infrastructure adapter only. Contains no business logic.

```
Airflow DAG
    └── calls ingest_folder(path, source)
              └── calls ingest_document_postgres(conn, doc)
              └── calls ingest_document_elasticsearch(es_client, doc)
```

### 🟢 API — `core/app/backend_api/`

FastAPI application exposing DocKA search capabilities over HTTP.

| Module | Responsibility |
|--------|---------------|
| `api_main.py` | App entrypoint, router registration, health check |
| `routers/search.py` | `GET /search` endpoint — validates input, calls service |
| `services/retrieval.py` | BM25 query construction, Elasticsearch call, result formatting |

### 🟢 UI — `core/app/frontend/`

Streamlit application providing a human-facing interface.

**Features:**
- Keyword search with highlighted snippets and relevance scores
- File upload (single, multiple, ZIP) with source tagging
- **Searchable: Temporary / Until I remove it** — per upload, **Temporary by default** (1 hour / 24 hours / 7 days)
- **Keep a copy of the original files** — per upload, **off by default**
- An info line stating exactly what will be stored, and for how long, before ingestion
- Sidebar showing ingested source tags, document counts, file retention (`files kept` / `text only`)
  and lifetime (`expires in …` / `until removed`)
- **Remove a source** — deletes it from search, PostgreSQL (incl. chunks) and its kept files
- System health check

**Upload retention — two independent choices:**

Searching requires storing the extracted text (chunks in PostgreSQL + search index).
The user decides how long that lasts, and separately whether the original files are kept.

| Searchable | Keep files | Stored | Until |
|------------|-----------|--------|-------|
| Temporary (default) | Off (default) | Extracted text | `expires_at`, then purged everywhere |
| Temporary | On | Extracted text + files in `data/uploads/<source>/` | `expires_at`, then purged everywhere |
| Until I remove it | Off | Extracted text | Source removed |
| Until I remove it | On | Extracted text + files | Source removed |

**Expiry enforcement** (`retention.py`, `pipelines/purge_expired.py`):
- `/search` excludes documents whose `expires_at` has passed — content stops being
  searchable **on time**, independent of the purge schedule
- The `docka_purge_expired` DAG runs every 15 minutes and deletes expired documents from
  Elasticsearch, PostgreSQL (chunks cascade) and their kept files; it is active on creation,
  so the promise never depends on someone unpausing a DAG
- Re-uploading known content can only **extend** retention, never shorten it

Because chunk text lives in PostgreSQL, the index stays rebuildable even when an original
file was not kept.
Source tags become folder names, so `storage.source_upload_dir()` rejects tags that would
escape `data/uploads/` (e.g. `../x`).

**Source removal** (`pipelines/remove_source.py`): Elasticsearch first, then PostgreSQL
(chunks cascade), then kept files — so a partial failure never leaves content searchable.
Folders ingested by Airflow (`data/samples/`) are never deleted.

**Architecture note:** The UI calls `ingest_folder()` directly for uploads,
bypassing Airflow. This gives immediate feedback to the user.
Airflow handles scheduled/batch ingestion only.

---

## Data Flow

### Ingestion Flow

```
File on disk / User upload
        │
        ▼
[1] file_checksum(path)
        │
        ├── checksum exists in PostgreSQL? → SKIP (idempotent)
        │
        ▼
[2] extractor.extract(path)          ← format-specific (PDF, DOCX, HTML, TXT)
        │
        ▼
[3] normalize_text(raw_content)      ← clean whitespace, page numbers, encoding
        │
        ▼
[4] detect_language(content)         ← 'fr', 'en', or None
        │
        ▼
[5] Build normalized document dict
    {
        doc_id:     uuid4(),
        source:     "sample" | user-defined tag,
        path:       original file path,
        title:      filename stem,
        language:   detected language,
        content:    normalized text,
        checksum:   sha256 hash,
        created_at: UTC timestamp
    }
        │
        ├──▶ [6a] insert_document(conn, doc)       → PostgreSQL (metadata only)
        │
        └──▶ [6b] index_document(es_client, doc)   → Elasticsearch (full content)
```

### Search Flow

```
User query: "bluetooth alarme"
        │
        ▼
FastAPI GET /search?q=bluetooth+alarme&size=10
        │
        ▼
retrieval.search_documents(query, size)
        │
        ▼
Elasticsearch multi_match query
    {
        fields: ["title^3", "content"],
        type: "best_fields",
        fuzziness: "AUTO"
    }
        │
        ▼
BM25 ranking + highlight extraction
        │
        ▼
JSON response
    {
        query: "bluetooth alarme",
        total: 7,
        results: [
            {
                doc_id, title, source, path,
                language, score, snippet (with <em> tags)
            }
        ]
    }
        │
        ▼
Streamlit renders results with scores and highlighted snippets
```

---

## Database Design

### PostgreSQL — `docka_app`

Source of truth for document metadata.

```sql
CREATE TABLE documents (
    id         SERIAL PRIMARY KEY,
    doc_id     TEXT UNIQUE NOT NULL,      -- UUID, stable document identifier
    source     TEXT NOT NULL,             -- origin tag (e.g. "sample", "healthcare")
    path       TEXT NOT NULL,             -- original file path
    title      TEXT,                      -- document title (filename stem)
    language   TEXT,                      -- detected language code ('fr', 'en', ...)
    checksum   TEXT UNIQUE NOT NULL,      -- SHA-256 hash (idempotency key)
    file_retained BOOLEAN NOT NULL DEFAULT TRUE,  -- FALSE: upload's original file not kept
    expires_at TIMESTAMPTZ,                       -- temporary uploads: purged after this (NULL = until removed)
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_documents_checksum ON documents(checksum);
CREATE INDEX idx_documents_doc_id   ON documents(doc_id);
```

**Key constraint:** `checksum UNIQUE` — this is the idempotency enforcement.
Attempting to insert a document with an existing checksum silently does nothing (`ON CONFLICT DO NOTHING`).

### PostgreSQL — `chunks` (Phase 2)

Token-bounded passages of each document — the unit embedded and retrieved from Phase 2 on.

```sql
CREATE TABLE IF NOT EXISTS chunks (
    id SERIAL PRIMARY KEY,
    chunk_id TEXT UNIQUE NOT NULL,     -- "<doc_id>:<chunk_index>"
    doc_id TEXT NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    start_char INT NOT NULL,           -- position in the normalized document
    end_char INT NOT NULL,
    token_count INT NOT NULL,
    created_at TIMESTAMP DEFAULT now(),
    UNIQUE (doc_id, chunk_index)
);
```

**Key decisions:**
- Chunk length is measured with the **embedding model's tokenizer** (`multilingual-e5-base`):
  500 tokens + 2 special tokens + the 2-token `passage: ` prefix stays under the model's 512 limit
- 50-token overlap so a sentence crossing a boundary is retrievable from either side
- Chunk text is sliced from the document by character offsets — `start_char` / `end_char`
  become citation anchors in Phase 3
- Created by `ensure_schema()` at pipeline start, so existing databases need no volume reset

### PostgreSQL — `docka_airflow`

Airflow internal metadata database. Completely isolated from application data.
Managed entirely by Airflow — DocKA never reads or writes to this database.

### Elasticsearch — `docka_documents`

Search index. Stores full document content for BM25 retrieval.
Mapping file: `core/ingestion/mappings/docs_v1.json`, applied by `ensure_index()` when the index is created.

```json
{
  "mappings": {
    "properties": {
      "doc_id":     { "type": "keyword" },
      "source":     { "type": "keyword" },
      "path":       { "type": "keyword", "index": false },
      "title":      { "type": "text", "analyzer": "standard" },
      "content":    { "type": "text", "analyzer": "standard" },
      "language":   { "type": "keyword" },
      "checksum":   { "type": "keyword" },
      "created_at": { "type": "date" }
    }
  }
}
```

**Key decisions:**
- `path` is `index: false` — stored but not searchable (no value in searching it)
- `checksum` is an indexed `keyword` — the ingestion idempotency check runs a `term` query on it
- `title` is boosted 3x at query time (`title^3`) — title matches rank higher than content matches
- `content.keyword` is ignored for very long texts — this is expected Elasticsearch behavior

---

## Ingestion Architecture

### Layered Design

```
┌─────────────────────────────────────────────┐
│  Layer 4 — Airflow (Infrastructure Adapter) │  🔵 schedules only
├─────────────────────────────────────────────┤
│  Layer 3 — Pipelines (Thin Orchestration)   │  🟡 assembly
├─────────────────────────────────────────────┤
│  Layer 2 — Extractors (Format-Specific)     │  🔴 text extraction
├─────────────────────────────────────────────┤
│  Layer 1 — Core (Pure Logic)                │  🔴 checksum, normalize, persist
└─────────────────────────────────────────────┘
```

### Idempotency Strategy

DocKA uses **content-based checksums** (SHA-256) as the idempotency key.

```
Same file content → Same checksum → INSERT skipped (both PG and ES)
Modified file     → New checksum  → INSERT succeeds → new document version
```

This means:
- Re-running the pipeline on the same folder is always safe
- Airflow retries never create duplicate documents
- User re-uploads of unchanged files are silently skipped

### Extractor Registry Pattern

```python
EXTRACTOR_REGISTRY = {
    ".pdf":  PDFExtractor,
    ".txt":  TXTExtractor,
    ".docx": DOCXExtractor,
    ".html": HTMLExtractor,
}
```

The loader dispatches to the correct extractor based on file extension.
Adding a new format = adding one file + one line in the registry.

---

## Search Architecture

### BM25 — How It Works

BM25 (Best Match 25) is the ranking algorithm used in Phase 1.
It scores documents based on three factors:

```
Score = Σ IDF(term) × TF(term, doc) × (k1 + 1)
                      ─────────────────────────────
                      TF(term, doc) + k1 × (1 - b + b × |doc| / avgdl)
```

Where:
- **TF** (Term Frequency) — how often the term appears in the document
- **IDF** (Inverse Document Frequency) — how rare the term is across all documents
- **|doc| / avgdl** — document length normalization (prevents long docs from dominating)
- **k1, b** — tuning parameters (Elasticsearch defaults: k1=1.2, b=0.75)

**In practice for DocKA:**
- `title^3` boost — a query match in the title is worth 3× a match in content
- `fuzziness: AUTO` — tolerates minor typos (1 edit for short words, 2 for longer)
- `best_fields` — uses the best-matching field score, not the sum

### Highlighted Snippets

Elasticsearch returns highlighted fragments with matched terms wrapped in `<em>` tags:

```
"L'adresse <em>bluetooth</em> est inscrite au dos de la borne."
```

DocKA returns up to 2 fragments of 200 characters each per document,
joined by ` ... ` in the UI.

---

## Infrastructure

### Docker Compose Services

```
┌──────────────────────────────────────────────────────────┐
│                    Docker Network: docka                  │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────────┐  │
│  │   api    │  │    ui    │  │       postgres         │  │
│  │  :8000   │  │  :8501   │  │        :5432           │  │
│  └──────────┘  └──────────┘  │  docka_app             │  │
│                               │  docka_airflow         │  │
│  ┌──────────────────────┐    └───────────────────────┘  │
│  │    elasticsearch     │                                │
│  │       :9200          │    ┌───────────────────────┐  │
│  └──────────────────────┘    │        redis           │  │
│                               │        :6379           │  │
│  ┌──────────────────────┐    └───────────────────────┘  │
│  │  airflow-webserver   │                                │
│  │       :8088          │    ┌───────────────────────┐  │
│  ├──────────────────────┤    │       pgadmin          │  │
│  │  airflow-scheduler   │    │        :5050           │  │
│  ├──────────────────────┤    └───────────────────────┘  │
│  │  airflow-worker      │                                │
│  ├──────────────────────┤                                │
│  │  airflow-triggerer   │                                │
│  └──────────────────────┘                                │
└──────────────────────────────────────────────────────────┘
```

### Port Reference

| Service | Port | Purpose |
|---------|------|---------|
| Streamlit UI | 8501 | User interface |
| FastAPI | 8000 | Search API |
| Airflow | 8088 | Pipeline orchestration |
| Elasticsearch | 9200 | Search engine |
| PostgreSQL | 5432 | Metadata store |
| pgAdmin | 5050 | Database UI |
| Redis | 6379 | Celery broker |

### Volume Strategy

| Volume | Purpose |
|--------|---------|
| `postgres_data` | Persistent database storage |
| `elasticsearch_data` | Persistent search index |
| `./data` → `/data` | Document storage (samples + uploads) |
| `./Ingestion` → `/opt/airflow/Ingestion` | Ingestion code in Airflow worker |

---

## Key Design Decisions

### Why Elasticsearch over a vector database?
Phase 1 is keyword search (BM25). Elasticsearch is the industry standard for this.
In Phase 2, Elasticsearch will be extended with vector search capabilities (dense_vector fields),
making it a hybrid search engine. No database migration needed.

### Why Airflow 2.10 over 3.x?
Airflow 3.x introduced a JWT-based execution API between the scheduler and workers.
In multi-container Docker setups, this caused persistent authentication failures
with no configuration workaround. Airflow 2.10 with CeleryExecutor is stable,
production-proven, and handles the same workloads without this issue.

### Why two separate PostgreSQL databases?
`docka_app` and `docka_airflow` are isolated databases on the same PostgreSQL instance.
This prevents Airflow's internal metadata from polluting the application schema,
allows independent backups, and follows the principle of least privilege.

### Why call the pipeline directly from Streamlit for uploads?
User uploads expect immediate feedback — typically under 5 seconds.
Routing through Airflow adds 10-30 seconds of scheduling overhead.
The pipeline is framework-agnostic by design, so calling it directly
from Streamlit is architecturally correct, not a workaround.

### Why SHA-256 for checksums?
SHA-256 produces a 64-character hex digest with negligible collision probability
for document-sized inputs. It reads files in 8KB chunks, making it memory-efficient
for large PDFs. The checksum is computed on raw bytes (before extraction),
so it detects any file change — even metadata changes not visible in the text.