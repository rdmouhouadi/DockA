# DocKA  
**Document–Knowledge–Access (DocKA)** is a modular **Information Retrieval (IR) platform**
designed to make large collections of technical documents easily searchable.

While the long-term vision is to support enterprise use cases such as
technical support and operations, the primary goal of this project is to
**document my learning journey in Information Retrieval systems**,
from classical keyword search to modern Retrieval-Augmented Generation (RAG).

Each phase delivers a **standalone, usable system**, while progressively
introducing more advanced IR concepts and tooling.

---

## 🧠 Vision

DocKA is designed as a **core knowledge platform**, not a single-purpose application.

At its core, DocKA provides:
- Document ingestion and normalization
- Robust search and retrieval APIs
- Observability and evaluation hooks

Domain-specific applications (e.g. technical support for smart metering systems)
are intended to be built **on top of DocKA**, without modifying its core.

---

## 🛤️ Roadmap

The roadmap is structured into **three progressive and standalone phases**.
Each phase reflects a concrete step in my learning curve while remaining
architecturally consistent with enterprise-grade IR systems.

---

## 📌 Phase 1 — Keyword Search (MVP)

**🎯 Objective**  
Build a robust and explainable baseline using classical IR techniques.

### Scope
- **Ingestion (Airflow DAGs)**
  - Watch folder / SharePoint
  - Extract text (PDF, DOCX, HTML)
  - Clean and normalize content
  - Detect language
- **Storage**
  - PostgreSQL for document metadata
  - Elasticsearch for keyword search (BM25)
- **Query**
  - Streamlit UI
  - FastAPI `/search` endpoint
  - BM25 ranking with snippets
- **Observability**
  - Airflow UI
  - Basic latency and query volume metrics
- **Security**
  - Internal access only
  - Basic authentication

### Exit Criteria
- p95 search latency < **500 ms**
- Reindexing DAG is idempotent and reliable
- Search quality exceeds a simple baseline

---

## 📌 Phase 2 — Semantic Search (Hybrid BM25 + Vectors)

**🎯 Objective**  
Enable natural-language queries by introducing semantic retrieval,
while preserving keyword search.

### Scope
- Chunk documents (sections / paragraphs)
- Embed chunks with a multilingual transformer model
- Store embeddings in a vector database (FAISS / Qdrant / Weaviate)
- Hybrid retrieval:
  - BM25 (Elasticsearch)
  - Vector similarity search
  - Reciprocal Rank Fusion (RRF)
- Feedback loop:
  - User relevance signals stored in PostgreSQL
- Retrieval mode toggles:
  - `bm25 | vector | hybrid`

### Exit Criteria
- Improved Recall and NDCG compared to Phase 1
- p95 latency < **800 ms**
- Feedback data visible and queryable

---

## 📌 Phase 3 — Retrieval-Augmented Generation (RAG)

**🎯 Objective**  
Provide natural-language answers grounded in documents,
with explicit citations and guardrails.

### Scope
- Query understanding and expansion
- Hybrid retrieval (BM25 + semantic)
- Context building (deduplication, chunk merging)
- Prompting with citation format
- LLM-based answer generation
- Guardrails:
  - Token limits
  - Out-of-scope refusal
- Endpoints:
  - `POST /ask` → `{ answer, citations }`
  - `POST /chat` → multi-turn interactions
- Observability:
  - Tracing with Langfuse
  - Evaluation with RAGAS

### Exit Criteria
- >80% of answers judged useful and faithful
- Zero hallucinations on curated test set
- p95 latency < **3 seconds**
- Every answer contains at least one valid citation

---

## 🏗️ Cross-Phase Engineering Principles

- Layered architecture (routers, services, adapters, repositories)
- Stable contracts and versioned schemas
- Idempotent ingestion pipelines with backfill support
- Strong focus on evaluation and observability
- Unit tests and relevance tests
- CI/CD-ready (Docker-based)
- Security-first mindset (private network, secrets management)

---

## 🚀 Future Extensions

Once DocKA core is stable, it will serve as the foundation for
**domain-specific support applications**, starting with:

- Technical support for **postpaid smart metering solutions**
- Later extension to **prepaid smart metering solutions**

These extensions will be implemented as **support modules**
built on top of DocKA, without altering its core architecture.

---

## 📌 Status

🚧 Active development — Phase 1 (Keyword Search MVP)

