# 📥 DocKA — Ingestion Architecture

This directory implements the **document ingestion layer** of **DocKA Core**.

The goal of this layer is to transform raw, heterogeneous documents
(PDF, Word, HTML, text, etc.) into a **clean, searchable knowledge base**
while remaining:

- **Domain-agnostic**
- **Reusable**
- **Idempotent**
- **Orchestration-independent**

In this context, **DocKA Core** refers to all logic that is:
- independent of execution environment
- independent of scheduling
- independent of downstream consumers (search, support, agents)

Anything that depends on infrastructure (e.g. Airflow) is treated as an adapter.

This design intentionally separates **pure logic** from **infrastructure concerns**
(e.g. Airflow), so that the same ingestion code can be reused across
different execution environments — including CLI scripts, Airflow DAGs,
Streamlit upload handlers, and unit tests.

---

## 🧭 Design Principles

### 1️⃣ Core First, Orchestration Later
DocKA ingestion logic must **not depend on Airflow** or any scheduler.
Airflow is treated as an *adapter*, not a dependency.

### 2️⃣ Single Responsibility
Each layer has a clearly defined role:
- Core logic
- Format-specific extraction
- Pipeline orchestration
- Infrastructure scheduling

### 3️⃣ Idempotency by Design
Ingestion can be safely re-run without duplicating documents,
thanks to checksum-based detection.
Idempotency is enforced using content-based checksums (SHA-256), allowing safe re-ingestion,
backfills, and retries without duplicating documents.

### 4️⃣ Data Sovereignty
Nothing is indexed without explicit action.
Users control exactly what enters the knowledge base —
whether from a local folder, a user upload, or a web source they configure.

---

## 📜 Ingestion Contract

This section defines the **formal contract** between the different layers
of the DocKA ingestion system.

The purpose of this contract is to ensure that:
- ingestion logic remains consistent
- extractors are interchangeable
- pipelines remain stable as the system evolves

---

### 1️⃣ Raw Document (Input Contract)

A **Raw Document** represents a file discovered by the ingestion system
before any content extraction.

**Required fields:**

| Field | Description |
|----|----|
| `path` | Absolute or relative filesystem path |
| `filename` | File name |
| `extension` | File extension (pdf, docx, html, txt, …) |
| `checksum` | Content-based checksum (used for idempotency) |
| `source` | Origin of the document (filesystem, web_api, pubmed, upload, …) |

This contract is produced by the **loader** and consumed by extractors.

---

### 2️⃣ Extractor Contract

Each extractor must implement the following behavior:

**Input**
- A single Raw Document

**Output**
- Extracted textual content
- Minimal metadata inferred from the document

**Guaranteed output fields:**

| Field | Description |
|----|----|
| `content` | Extracted raw text |
| `title` | Document title (if available) |
| `language` | Detected or inferred language |
| `metadata` | Optional format-specific metadata |

Extractors:
- must not perform persistence
- must not perform deduplication
- must not depend on orchestration frameworks

---

### 3️⃣ Normalized Document (Core Output)

After extraction and normalization, documents are represented internally
as **Normalized Documents**.

**Guaranteed fields:**

| Field | Description |
|----|----|
| `doc_id` | Stable document identifier (UUID) |
| `source` | Document origin tag |
| `path` | Original path or URL |
| `title` | Normalized title |
| `language` | Detected language code (e.g. `fr`, `en`) |
| `content` | Cleaned, normalized text |
| `checksum` | SHA-256 content hash |
| `created_at` | UTC timestamp of ingestion |

This representation is the **canonical form** used by DocKA Core.

---

### 4️⃣ Persistence Guarantees

DocKA ingestion guarantees that:

- Documents are ingested **idempotently**
- Re-ingesting unchanged documents does not create duplicates
- Metadata persistence is atomic
- Content extraction and persistence are decoupled

**PostgreSQL** is the source of truth for document metadata.  
**Elasticsearch** is a disposable search index — it can be rebuilt at any time
by re-running the ingestion pipeline.

---

### 5️⃣ Contract Stability

This ingestion contract is considered **stable** across DocKA Core versions.

Future extensions (semantic search, RAG, web ingestion, agents) must:
- extend this contract without breaking it
- or introduce new contracts explicitly

---

## 🗂️ Folder Structure Overview

```bash
Ingestion/
├── README.md
├── __init__.py
│
├── core/                    # 🔴 DocKA Core (pure logic)
│   ├── __init__.py
│   ├── loader.py            # scan folders, dispatch to extractors
│   ├── checksum.py          # SHA-256 idempotency hashing
│   ├── normalizer.py        # text cleaning and unicode normalization
│   ├── repository.py        # PostgreSQL access
│   └── es_repository.py     # Elasticsearch access
│
├── extractors/              # 🔴 DocKA Core (format-specific)
│   ├── __init__.py          # extractor registry
│   ├── pdf.py               # PDF extraction (pypdf)
│   ├── docx.py              # Word extraction (python-docx)
│   ├── html.py              # HTML extraction (BeautifulSoup4)
│   └── txt.py               # Plain text extraction
│
├── pipelines/               # 🟡 Thin orchestration (reusable)
│   ├── __init__.py
│   ├── ingest_folder.py     # folder orchestrator — calls sub-pipelines
│   ├── ingest_postgres.py   # one document → PostgreSQL
│   └── ingest_elasticsearch.py  # one document → Elasticsearch
│
├── sources/                 # 🟡 Web source adapters (Phase 4)
│   ├── __init__.py
│   ├── pubmed.py            # PubMed E-utilities API fetcher
│   └── web_crawler.py       # generic URL fetcher
│
└── airflow/                 # 🔵 Infrastructure adapter
    ├── dags/
    │   ├── ingest_documents.py      # filesystem ingestion DAG
    │   └── ingest_web_source.py     # web ingestion DAG (Phase 4)
    └── README.md
```

---

## 🔴 Layer 1 — DocKA Core (Pure Logic)

**Location:** `Ingestion/core/`

This layer contains **pure, reusable ingestion logic**.
It has **no knowledge of Airflow, scheduling, or infrastructure**.

### Responsibilities

- Discover documents in a filesystem
- Compute deterministic checksums
- Normalize extracted text
- Detect document language
- Persist document metadata in PostgreSQL
- Index document content in Elasticsearch
- Guarantee idempotent ingestion in both stores

### Key Modules

- **`loader.py`**
  Scans directories and dispatches files to the correct extractor
  via the extractor registry.

- **`checksum.py`**
  Computes SHA-256 content hashes to detect duplicates and updates.
  Reads files in 8KB chunks for memory efficiency.

- **`normalizer.py`**
  Cleans and standardizes extracted text:
  unicode normalization, control character removal,
  page number stripping, whitespace collapsing.

- **`repository.py`**
  Handles all PostgreSQL interactions.
  Uses `ON CONFLICT (checksum) DO NOTHING` for idempotency.

- **`es_repository.py`**
  Handles all Elasticsearch interactions.
  Creates the index with explicit mapping if it does not exist.
  Uses `doc_id` as the Elasticsearch document ID for idempotency.

### Milestone — Completion Criteria

- Documents are detected deterministically ✅
- Re-running ingestion does not create duplicates ✅
- Metadata is visible and correct in PostgreSQL ✅
- Content is indexed and searchable in Elasticsearch ✅
- No dependency on Airflow ✅

---

## 🔴 Layer 2 — DocKA Core (Format-Specific Extraction)

**Location:** `Ingestion/extractors/`

This layer handles **how text is extracted**, not *when* or *why*.

Each extractor:
- handles exactly one format
- returns clean text + minimal metadata
- contains no persistence logic

### Supported Formats

| File | Format | Library | Notes |
|------|--------|---------|-------|
| `pdf.py` | PDF | pypdf | Text layer extraction |
| `docx.py` | Word | python-docx | Paragraph-based extraction |
| `html.py` | HTML | BeautifulSoup4 | Strips tags, script, style |
| `txt.py` | Plain text | stdlib | UTF-8 with latin-1 fallback |

### Extractor Registry

All extractors are registered in `__init__.py`:

```python
EXTRACTOR_REGISTRY = {
    ".pdf":  PDFExtractor,
    ".txt":  TXTExtractor,
    ".docx": DOCXExtractor,
    ".html": HTMLExtractor,
}
```

**Design rule:** Adding a new format requires only creating a new extractor file
and adding one line to the registry. The pipeline never changes.

### Milestone — Completion Criteria

- All four extractors implemented and tested ✅
- Extractors return consistent outputs ✅
- Core pipeline unchanged when adding formats ✅

---

## 🟡 Layer 3 — Pipelines (Thin Orchestration)

**Location:** `Ingestion/pipelines/`

Pipelines assemble **core logic + extractors** into reusable workflows.
They are framework-agnostic — callable from Airflow DAGs, CLI scripts,
Streamlit upload handlers, or unit tests.

### Pipeline Architecture

Each sub-pipeline handles **one document, one destination**:

```
ingest_folder.py          ← coordinator
    ├── ingest_postgres.py    ← one doc → PostgreSQL
    └── ingest_elasticsearch.py  ← one doc → Elasticsearch
```

### `ingest_folder.py` — Full Pipeline

1. Scan directory recursively
2. Compute SHA-256 checksum
3. Check idempotency (skip if checksum exists in PostgreSQL)
4. Extract text content (format-specific extractor)
5. Normalize text (`normalizer.py`)
6. Detect language (`langdetect`)
7. Build normalized document dict
8. Persist metadata → PostgreSQL
9. Index content → Elasticsearch
10. Log summary (ingested / skipped / failed / duration)

### `ingest_postgres.py` — PostgreSQL Sub-Pipeline

- Checks if checksum already exists
- Inserts document metadata if new
- Returns `True` (inserted) or `False` (skipped)

### `ingest_elasticsearch.py` — Elasticsearch Sub-Pipeline

- Checks if checksum already indexed
- Indexes full document content if new
- Returns `True` (indexed) or `False` (skipped)

### Why This Split?

- Each store can be updated independently
- Elasticsearch can be rebuilt without touching PostgreSQL
- Failures in one store do not corrupt the other
- Each sub-pipeline is independently testable

### Milestone — Completion Criteria

- `ingest_folder` ingests a folder end-to-end ✅
- `ingest_postgres` and `ingest_elasticsearch` independently testable ✅
- Pipeline callable without Airflow ✅
- Idempotency verified across both stores ✅

---

## 🔵 Layer 4 — Airflow (Infrastructure Adapter)

**Location:** `Ingestion/airflow/`

This layer contains **no business logic**.

Its only role is to:
- schedule ingestion
- configure retries
- handle operational concerns

**Design rule:** Airflow must only call pipelines — never reimplement logic.

### Current DAGs

- **`ingest_documents.py`** — Scheduled filesystem ingestion.
  Triggers `ingest_folder(path, source)` on the configured data directory.

### Planned DAGs (Phase 4)

- **`ingest_web_source.py`** — Parameterized web ingestion.
  Accepts a domain + query, fetches from the configured source (PubMed, crawler),
  and triggers the ingestion pipeline.

### Milestone — Completion Criteria

- Airflow DAG triggers existing pipeline ✅
- No ingestion logic duplicated in DAGs ✅
- Failures visible in Airflow UI ✅
- Worker logs are JSON-structured ✅

---

## 🟡 Layer 5 — Sources (Web Adapters) *(Phase 4)*

**Location:** `Ingestion/sources/`

This layer will contain **web source adapters** for fetching documents
from external APIs and websites.

Each source adapter:
- fetches documents from one specific source
- returns them in the Raw Document format
- handles rate limiting, retries, and pagination

### Planned Sources

- **`pubmed.py`** — PubMed E-utilities API.
  Fetches abstracts and metadata by query.
  Primary source for the healthcare demo corpus.

- **`web_crawler.py`** — Generic URL fetcher.
  Fetches HTML pages from specified URLs.
  Used for custom domain ingestion.

---

## 🛣️ Ingestion Roadmap Summary

| Milestone | Focus | Status |
|-----------|-------|--------|
| M1 | Core logic (filesystem → PostgreSQL) | ✅ |
| M2 | Format extractors (PDF, DOCX, HTML, TXT) | ✅ |
| M3 | Reusable pipelines (folder, postgres, elasticsearch) | ✅ |
| M4 | Airflow scheduling | ✅ |
| M5 | Web source ingestion (PubMed, crawler) | ⬜ |
| M6 | Domain configuration & portal trigger | ⬜ |

---

## 🎯 Why This Architecture Matters

This ingestion design ensures that:

- DocKA Core remains **generic and reusable** across domains
- Domain-specific logic stays out of ingestion
- Airflow can be replaced without rewriting ingestion
- Elasticsearch can be rebuilt without data loss
- The system scales from POC to production
- Users maintain **full control** over what data is indexed

This foundation enables later phases:
- Semantic search (chunking + embeddings)
- RAG (retrieval-augmented generation)
- Web source ingestion (PubMed, crawlers)
- Domain portal (user-triggered corpus acquisition)
- AI agents

---

> **Ingestion is the backbone of DocKA.**  
> **If ingestion is clean, everything built on top remains simple.**