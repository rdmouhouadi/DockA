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
different execution environments.

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
Idempotency is enforced using content-based checksums, allowing safe re-ingestion,
backfills, and retries without duplicating documents.

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
| `source` | Origin of the document (filesystem, sharepoint, api, …) |

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
| `doc_id` | Stable document identifier |
| `source` | Document origin |
| `path` | Original path |
| `title` | Normalized title |
| `language` | Normalized language code |
| `content` | Cleaned, normalized text |
| `checksum` | Content checksum |

This representation is the **canonical form** used by DocKA Core.

---

### 4️⃣ Persistence Guarantees

DocKA ingestion guarantees that:

- Documents are ingested **idempotently**
- Re-ingesting unchanged documents does not create duplicates
- Metadata persistence is atomic
- Content extraction and persistence are decoupled

The PostgreSQL database is the **source of truth** for document metadata.

---

### 5️⃣ Contract Stability

This ingestion contract is considered **stable** across DocKA Core versions.

Future extensions (semantic search, RAG, support modules, agents) must:
- extend this contract without breaking it
- or introduce new contracts explicitly

---

## 🗂️ Folder Structure Overview

```bash
app/
├── ingestion/
│   ├── README.md
│   ├── __init__.py
│
│   ├── core/                # 🔴 DocKA Core (pure logic)
│   │   ├── __init__.py
│   │   ├── loader.py        # scan folders
│   │   ├── checksum.py     # idempotency
│   │   ├── normalizer.py   # text cleanup
│   │   ├── repository.py   # Postgres access
│   │
│   ├── extractors/          # 🔴 DocKA Core (format-specific)
│   │   ├── __init__.py
│   │   ├── pdf.py
│   │   ├── docx.py
│   │   ├── html.py
│   │   └── txt.py
│
│   ├── pipelines/           # 🟡 Thin orchestration (reusable)
│   │   ├── __init__.py
│   │   └── ingest_folder.py
│
│   ├── airflow/             # 🔵 Infrastructure adapter
│   │   ├── dags/
│   │   │   └── ingest_documents.py
│   │   └── README.md
```

---

## 🔴 Layer 1 — DocKA Core (Pure Logic)

**Location:** `ingestion/core/`

This layer contains **pure, reusable ingestion logic**.
It has **no knowledge of Airflow, scheduling, or infrastructure**.

### Responsibilities

- Discover documents in a filesystem
- Compute deterministic checksums
- Normalize extracted text
- Persist document metadata in PostgreSQL
- Guarantee idempotent ingestion

### Key Modules

- `loader.py`  
  Scans directories and yields supported files.

- `checksum.py`  
  Computes content-based hashes to detect duplicates and updates.

- `normalizer.py`  
  Cleans and standardizes extracted text (whitespace, encoding, noise).

- `repository.py`  
  Handles all PostgreSQL interactions (insert, existence checks).

### Milestone — Completion Criteria

- Documents are detected deterministically
- Re-running ingestion does not create duplicates
- Metadata is visible and correct in PostgreSQL
- No dependency on Airflow or Elasticsearch

---

## 🔴 Layer 2 — DocKA Core (Format-Specific Extraction)

**Location:** `ingestion/extractors/`

This layer handles **how text is extracted**, not *when* or *why*.

Each extractor:
- handles exactly one format
- returns clean text + minimal metadata
- contains no persistence logic

### Supported Formats (initial)

- `txt.py` — Plain text (baseline extractor)
- `html.py` — HTML and email-like documents
- `pdf.py` — Technical and vendor PDFs
- `docx.py` — Word documents

### Design Rule

> Adding a new format must only require creating a new extractor file.

### Milestone — Completion Criteria

- At least one extractor (TXT) works end-to-end
- Extractors return consistent outputs
- Core pipeline remains unchanged when adding formats

---

## 🟡 Layer 3 — Pipelines (Thin Orchestration)

**Location:** `ingestion/pipelines/`

Pipelines assemble **core logic + extractors** into reusable workflows.

They:
- define execution order
- call core functions
- remain framework-agnostic

### Example Pipeline

`ingest_folder.py`:
1. Scan directory
2. Compute checksum
3. Select appropriate extractor
4. Normalize content
5. Persist metadata

### Why Pipelines Exist

- To allow reuse across:
  - CLI scripts
  - Airflow DAGs
  - Tests
  - Future APIs

### Milestone — Completion Criteria

- One pipeline ingests a folder end-to-end
- Pipeline can be called without Airflow
- Logic is readable and debuggable

---

## 🔵 Layer 4 — Airflow (Infrastructure Adapter)

**Location:** `ingestion/airflow/`

This layer contains **no business logic**.

Its only role is to:
- schedule ingestion
- configure retries
- handle operational concerns

### Design Rule

> Airflow must only call pipelines — never reimplement logic.

### Milestone — Completion Criteria

- Airflow DAG triggers existing pipeline
- No ingestion logic duplicated in DAGs
- Failures are visible in Airflow UI

---

## 🛣️ Ingestion Roadmap Summary

| Milestone | Focus | Status |
|---------|------|-------|
| M1 | Core logic (filesystem → DB) | ✅ |
| M2 | Format extractors | ⏳ |
| M3 | Reusable pipelines | ⬜ |
| M4 | Airflow scheduling | ⬜ |

---

## 🎯 Why This Architecture Matters

This ingestion design ensures that:

- DocKA Core remains **generic and reusable**
- Domain-specific logic (e.g. support, tickets) stays out of ingestion
- Airflow can be replaced without rewriting ingestion
- The system scales from POC to production

This foundation enables later phases:
- Elasticsearch indexing
- Semantic search
- RAG
- Support-specific modules
- AI agents

---

> **Ingestion is the backbone of DocKA.  
> If ingestion is clean, everything built on top remains simple.**
