<div align="center">

# 📘 DocKA
### Domain Knowledge Acquisition & Retrieval Platform

*From raw documents to searchable knowledge — in any domain.*

![Version](https://img.shields.io/badge/version-v0.1.0--POC-blue)
![License](https://img.shields.io/badge/license-AGPL--3.0-green)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Status](https://img.shields.io/badge/status-Phase%201%20Complete-brightgreen)

**Author:** Richie Mouhouadi

</div>

---

## 🧭 What is DocKA?

DocKA is an open-source **Domain Knowledge Acquisition & Retrieval Platform**.

It transforms raw, heterogeneous documents — PDFs, Word files, HTML pages, plain text —
into a **clean, searchable knowledge base**, using a modular pipeline that is:

- **Domain-agnostic** — works on any corpus: technical docs, healthcare literature, legal texts
- **Idempotent** — safe to re-run without creating duplicates
- **Extensible** — designed to grow from keyword search to semantic search to RAG

DocKA is not just a search engine.  
It is a **knowledge acquisition system** — the infrastructure that makes documents *useful*.

---

## 🎯 Vision

Most organizations have documents scattered across folders, drives, and systems.  
Finding the right information requires knowing where to look — and often, that knowledge lives only in people's heads.

DocKA solves this by:

1. **Ingesting** documents from any source (filesystem, web APIs, user uploads)
2. **Normalizing** and indexing their content automatically
3. **Making them searchable** via keyword search (Phase 1), semantic search (Phase 2), and RAG (Phase 3)
4. **Attributing knowledge** to its source — with citations, scores, and traceability

**Most importantly, DocKA gives you full control over what data you make searchable.**  
In a world where data privacy is critical — especially in regulated industries like healthcare, legal, and finance —
you decide what enters the knowledge base. Nothing is indexed without explicit action.
Your documents stay on your infrastructure. No data leaves your environment.

**DocKA is also a documented learning journey.**  
The project is built incrementally — from the most basic notion of Information Retrieval  
(keyword search with BM25) to progressively more complex systems (semantic search, hybrid retrieval, RAG).  
Each phase is documented with the concepts learned, the mistakes made, and the resources used.  
The goal is not just to build a working system, but to deeply understand every component and to leave a reference that others can follow to learn the same path.

The long-term goal is a platform where a user selects a domain,
DocKA fetches the relevant knowledge base from the web,
and answers questions with cited, verifiable responses.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        DocKA Platform                        │
├─────────────────┬───────────────────────────────────────────┤
│   Data Sources  │  Filesystem · Web APIs · User Uploads     │
├─────────────────┴───────────────────────────────────────────┤
│                                                              │
│   ┌─────────────────────────────────────────────────────┐   │
│   │              Ingestion Pipeline (Airflow)            │   │
│   │  scan → checksum → extract → normalize → persist    │   │
│   └──────────────────┬──────────────────────────────────┘   │
│                       │                                      │
│          ┌────────────┴────────────┐                         │
│          ▼                         ▼                         │
│   ┌─────────────┐         ┌──────────────────┐              │
│   │  PostgreSQL  │         │  Elasticsearch   │              │
│   │  (metadata) │         │  (search index)  │              │
│   └─────────────┘         └────────┬─────────┘              │
│                                    │                         │
│                      ┌─────────────▼──────────┐             │
│                       │     FastAPI (/search)  │             │
│                       └─────────────┬──────────┘            │
│                                     │                        │
│                       ┌─────────────▼──────────┐            │
│                       │    Streamlit UI         │            │
│                       │  Search · Upload · Tags │            │
│                       └────────────────────────┘            │
└─────────────────────────────────────────────────────────────┘
```

**Key design decisions:**
- PostgreSQL is the **source of truth** for document metadata
- Elasticsearch is a **disposable index** — can be rebuilt from scratch at any time
- Airflow handles **scheduled/batch ingestion** — pipelines are framework-agnostic
- The UI calls the ingestion pipeline **directly** for interactive uploads

---

## ✅ Current Status — v0.1.0 (Phase 1 Complete)

| Component | Status | Description |
|-----------|--------|-------------|
| Ingestion pipeline | ✅ | Filesystem → PostgreSQL + Elasticsearch |
| PDF extraction | ✅ | Full text extraction with pypdf |
| DOCX extraction | ✅ | Word document support |
| HTML extraction | ✅ | Tag stripping with BeautifulSoup |
| TXT extraction | ✅ | UTF-8 and latin-1 support |
| Text normalization | ✅ | Cleaning, deduplication, unicode |
| Language detection | ✅ | Auto-detection via langdetect |
| BM25 search | ✅ | Ranked results with highlighted snippets |
| FastAPI `/search` | ✅ | REST endpoint with fuzziness |
| Streamlit UI | ✅ | Search + file upload + source tags |
| Airflow scheduling | ✅ | CeleryExecutor, DAG-based ingestion |
| Unit tests | ✅ | 32 tests — core, normalizer, extractors |

---

## 📚 A Documented Learning Journey

DocKA is built as a learning project as much as a technical one.

Each phase introduces new concepts, starting from fundamentals:

| Phase | Concepts Introduced |
|-------|-------------------|
| Phase 1 | Information Retrieval, BM25, inverted index, TF-IDF, text normalization, idempotency, orchestration |
| Phase 2 | Embeddings, vector search, cosine similarity, chunking strategies, hybrid retrieval, RRF, NDCG |
| Phase 3 | RAG architecture, prompt engineering, faithfulness, hallucination, RAGAS, LLM tracing |
| Phase 4 | Web crawling, API ingestion, domain ontologies, knowledge graphs |

Every concept is backed by a curated learning reference in [`docs/learning-references.md`](docs/learning-references.md).  
The troubleshooting log in [`docs/troubleshooting.md`](docs/troubleshooting.md) documents every error encountered and how it was resolved.

This is not a tutorial. It is my record of how I learnt to build a production system, including the wrong turns.

---

## 🗺️ Roadmap

### Phase 1 — POC: Keyword Search ✅
Filesystem ingestion → BM25 search → Streamlit UI

### Phase 2 — Semantic Search ⬜
Document chunking → multilingual embeddings → hybrid BM25 + vector retrieval → NDCG@10 evaluation

### Phase 3 — RAG ⬜
Retrieval-Augmented Generation → cited answers → RAGAS evaluation → Langfuse tracing

### Phase 4 — Domain Portal ⬜
Web source ingestion (PubMed, crawlers) → domain configuration → healthcare demo corpus

> See [`docs/roadmap.md`](docs/roadmap.md) for the full task-level breakdown.

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+

### 1 — Clone the repository

```bash
git clone https://github.com/rdmouhouadi/Docka.git
cd docka
```

### 2 — Create the environment file

```bash
cp infra/.env.example infra/.env
```

Edit `infra/.env` with your configuration (defaults work for local development).

### 3 — Start the platform

```bash
cd infra
docker compose up --build
```

### 4 — Access the services

| Service | URL |
|---------|-----|
| Streamlit UI | http://localhost:8501 |
| FastAPI docs | http://localhost:8000/docs |
| Airflow UI | http://localhost:8088 |
| pgAdmin | http://localhost:5050 |

### 5 — Ingest sample documents

In the Airflow UI (`http://localhost:8088`):
- Login: `admin` / `admin`
- Trigger the `ingest_documents` DAG

Or upload documents directly via the Streamlit UI at `http://localhost:8501`.

### 6 — Search

Open `http://localhost:8501` and search for any term in your documents.

---

## 🗂️ Project Structure

```
docka/
├── app/
│   ├── backend_api/          # FastAPI — search endpoint
│   │   ├── routers/
│   │   └── services/
│   ├── common/               # Shared utilities
│   └── frontend/             # Streamlit UI
│
├── Ingestion/
│   ├── core/                 # Pure ingestion logic (no framework deps)
│   │   ├── checksum.py
│   │   ├── loader.py
│   │   ├── normalizer.py
│   │   ├── repository.py
│   │   └── es_repository.py
│   ├── extractors/           # Format-specific extractors
│   │   ├── pdf.py
│   │   ├── docx.py
│   │   ├── html.py
│   │   └── txt.py
│   ├── pipelines/            # Framework-agnostic orchestration
│   │   ├── ingest_folder.py
│   │   ├── ingest_postgres.py
│   │   └── ingest_elasticsearch.py
│   └── airflow/              # Airflow adapter (DAGs only)
│       └── dags/
│
├── infra/
│   ├── docker/               # Dockerfiles
│   ├── elasticsearch/        # Index mappings
│   ├── postgres/             # Init SQL
│   └── docker-compose.yml
│
├── data/
│   ├── samples/              # Sample documents
│   └── uploads/              # User-uploaded documents
│
├── tests/
│   └── test_core.py          # Unit tests (32 tests)
│
└── docs/
    ├── architecture.md
    ├── roadmap.md
    ├── troubleshooting.md
    └── learning-references.md
```

---

## 🧪 Running Tests

```bash
# Install dependencies
pip install -r requirements.txt
pip install pytest

# Run all tests
pytest tests/ -v
```

---

## 🙏 Inspiration & Acknowledgements

DocKA was directly inspired by the **arXiv Paper Curator** project by [Jam With AI](https://github.com/jamwithai/production-agentic-rag-course) — a learner-focused course on building production RAG systems from the ground up.

That project demonstrated the right professional approach: **master keyword search foundations first, then enhance with semantic search and RAG**. DocKA follows the same philosophy.

**Where DocKA diverges:**
- Domain-agnostic by design — not tied to academic papers
- Emphasis on **data sovereignty** — you control what gets indexed, nothing leaves your infrastructure
- User-driven ingestion via file upload alongside scheduled pipeline ingestion
- Built around Elasticsearch rather than OpenSearch

Thanks to [jamwithai](https://jamwithai.substack.com) for making this learning path public.

---

## 📄 License

This project is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**.

You are free to use, study, and modify this software.  
**Commercial use requires open-sourcing your modifications** under the same license.

See the [LICENSE](LICENSE) file for details.

---

## 🤝 Contributing

Contributions are welcome. Please open an issue before submitting a pull request
so we can discuss the proposed change.

---

<div align="center">
<sub>Built with Python · FastAPI · Elasticsearch · Airflow · PostgreSQL · Streamlit</sub>
</div>