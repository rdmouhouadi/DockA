# DocKA — System Architecture

## 1. Purpose

DocKA (Document–Knowledge–Access) is a **modular Information Retrieval platform**
designed to ingest, index, and retrieve technical documents efficiently.

The architecture is intentionally:
- **Simple enough** for a single-engineer POC
- **Structured enough** to scale to enterprise support use cases
- **Explicitly layered** to support future AI agents and domain extensions

This document describes the **DocKA Core architecture** (knowledge platform only).
Domain-specific support logic (e.g. smart metering) is intentionally excluded at this stage.

---

## 2. Architectural Goals

- Clear separation between **ingestion**, **retrieval**, and **presentation**
- Decoupled batch (offline) and query-time (online) workloads
- Infrastructure that can be reproduced locally using Docker
- Observability at every stage (ingestion, search, generation)
- Architecture compatible with future AI agent integration

---

## 3. High-Level Architecture


---

## 4. Component Breakdown

### 4.1 Document Sources

**Role**
- Provide raw knowledge content

**Examples**
- Manufacturer documentation
- Network and protocol specifications
- Operational manuals

**Notes**
- Documents are immutable inputs
- Versioning is handled downstream

---

### 4.2 Ingestion Layer (Airflow)

**Role**
- Orchestrate document ingestion as batch jobs

**Responsibilities**
1. Detect new or updated documents
2. Extract raw text
3. Clean and normalize content
4. Detect language
5. Chunk documents (future phases)
6. Store metadata
7. Index content into search systems

**Why Airflow?**
- Clear DAG visualization
- Retry and backfill support
- Industry-standard for data pipelines

**Key Design Rule**
> Ingestion must be **idempotent**  
> Re-running a DAG should never duplicate data.

---

### 4.3 Metadata Store (PostgreSQL)

**Role**
- Store authoritative document metadata

**Typical Fields**
- Document ID
- Source path / URI
- Title
- Language
- Author (if available)
- Checksum / hash
- Ingestion timestamp

**Why PostgreSQL?**
- Strong consistency
- Structured queries
- Easy integration with Airflow and FastAPI

**Important**
PostgreSQL does **not** store full document text for retrieval.

---

### 4.4 Search Index (Elasticsearch)

**Role**
- Provide fast and explainable keyword search

**Responsibilities**
- Index cleaned document text
- Apply language-specific analyzers
- Rank results using BM25

**Indexing Strategy**
- One index per schema version (e.g. `docka_docs_v1`)
- Index is disposable and rebuildable

**Why Elasticsearch first?**
- Transparent scoring (BM25)
- Mature ecosystem
- Excellent baseline for IR learning

---

### 4.5 Retrieval API (FastAPI)

**Role**
- Act as the **single entry point** for all retrieval logic

**Responsibilities**
- Accept user queries
- Validate inputs
- Execute retrieval strategies
- Format ranked results
- Expose stable APIs

**Initial Endpoints**
- `POST /search`

**Future Endpoints**
- `/ask` (RAG)
- `/chat` (multi-turn)
- `/feedback`

**Key Rule**
> No domain-specific logic lives here.

---

### 4.6 User Interface (Streamlit)

**Role**
- Human-facing interface for DocKA

**Responsibilities**
- Query input
- Result visualization
- Snippet inspection
- Debug and demo support

**Why Streamlit?**
- Fast iteration
- Minimal frontend overhead
- Ideal for POCs and internal tools

---

## 5. Data Flow (Phase 1)

### Ingestion Flow

Document --> Extract --> Clean --> Language Detect --> Store Metadata (PostgreSQL) --> Index text (Elasticsearch)

### Query Flow

User Query --> FastAPI --> Elasticsearch (BM25) --> Ranked Results --> UI


---

## 6. Deployment Model (POC)

DocKA Core is deployed locally using **Docker Compose**.

### Containers

- PostgreSQL
- Elasticsearch
- Airflow (webserver + scheduler)
- FastAPI service
- Streamlit UI

### Networking

- Single private Docker network
- No public exposure except UI/API ports

---

## 7. Observability

| Component      | Observability Mechanism |
|---------------|--------------------------|
| Airflow       | Web UI, task logs        |
| API           | Request logs, latency   |
| Elasticsearch | Query profiling          |

---

## 8. Non-Goals (for Phase 1)

- Authentication / authorization
- Multi-tenancy
- High availability
- AI agent orchestration

These are **deliberately postponed**.

---

## 9. Forward Compatibility

This architecture explicitly supports future additions:

- Vector databases (semantic search)
- RAG pipelines
- AI support agents
- Domain-specific support modules
- Multi-solution smart metering support

No core redesign is required to support these extensions.

---

## 10. Summary

DocKA Core is:
- A **clean IR platform**
- A **learning-first system**
- A **foundation for support automation**

This architecture will be implemented incrementally,
starting with Docker-based local deployment.
