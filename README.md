# DocKA  
"**Documents-Knowledge-Access (DocKA)**" is an **Information Retrieval (IR) system** that makes your documents easily searchable.  

---

# 🛤️ Roadmap  

While the long-term vision is to build a production-ready Information Retrieval (IR) System for enterprise teams and departments, the **core purpose** of this project is to document my learning journey.  
Each stage reflects how I progressively develop new skills in the IR domain. 
To capture this growth, the roadmap is structured into **three standalone phases**, where every phase delivers a usable version of the solution.

---

## 📌 Phase 1 — Keyword Search (MVP)  

**🎯 Objective**: Implement a robust baseline system using classic Information Retrieval (IR) methods.  

- **Ingestion (Airflow DAGs)**  
  - Watch folder / SharePoint → extract text → clean → detect language  
  - Store metadata in **PostgreSQL**  
  - Index docs in **Elasticsearch**  

- **Storage**  
  - PostgreSQL → document metadata (id, path, title, lang, author, checksum)  
  - Elasticsearch → index `docKA_v1` with analyzers for English/French  

- **Query**  
  - **Streamlit UI** → **FastAPI** `/search` → **BM25 ranking** → return results with snippets  

- **Observability**  
  - Basic metrics (latency, query volume)  
  - Airflow UI for pipelines  

- **Security**  
  - Internal access only  
  - Basic authentication  

✅ **Exit Criteria**  
- p95 search latency < **500ms** (200–1k docs)  
- Precision@10 ≥ baseline (curated queries)  
- One-click reindex DAG works reliably  

---

## 📌 Phase 2 — Semantic Search (Hybrid BM25 + Vectors)  

**🎯 Objective**: Enable natural-language queries with semantic understanding, while keeping keyword search.  

- **Ingestion Upgrades**  
  - Chunk documents (sections/tables)  
  - Embed chunks with multilingual transformer model  
  - Store embeddings in **Vector DB** (Qdrant / Weaviate / ES vectors)  

- **Hybrid Retrieval**  
  - Combine BM25 (Elasticsearch) + vector search  
  - Merge results with **Reciprocal Rank Fusion (RRF)**  

- **Feedback Loop**  
  - Endpoint to log user judgments (👍 / 👎)  
  - Store feedback in PostgreSQL  

- **Evaluation Toggles**  
  - bm25 | vector | hybrid  

✅ **Exit Criteria**  
- Improved **NDCG@10** and **Recall@10** vs Phase 1  
- p95 latency < **800ms**  
- Feedback logs visible in dashboard  

---

## 📌 Phase 3 — Retrieval-Augmented Generation (RAG)  

**🎯 Objective**: Provide natural language answers, grounded in documents, with proper citations.  

- **Query Pipeline**  
  - Query understanding (rewrite/expansion)  
  - Hybrid retriever (BM25 + semantic)  
  - Context builder (dedupe, merge chunks, metadata)  
  - Prompting (multilingual, citation format)  
  - Generation (LLM call with streaming)  
  - Guardrails (max tokens, refusal for out-of-scope)  

- **Endpoints**  
  - `POST /ask` → returns `{answer, citations}`  
  - `POST /chat` → multi-turn with memory  

- **Observability**  
  - Trace retrieval + generation with **Langfuse**  
  - Evaluate with **RAGAS**  

✅ **Exit Criteria**  
- ≥80% of answers judged **useful & faithful**  
- Zero hallucinations on curated test set  
- p95 latency < **2.5s**  
- Every answer contains ≥1 valid citation  

---

## 🏗️ Cross-Phases 

- **Layered Design**: routers, services, adapters, repositories, common utils  
- **Contracts & Schemas**: versioned APIs, stable doc/chunk schemas  
- **Ingestion**: idempotent DAGs, delta updates, backfill support  
- **Quality**: unit tests, relevance tests, linting, typed code  
- **CI/CD**: GitHub Actions → Docker images → deployments  
- **Security**: private network, OIDC SSO, secrets in vaults  
- **Metrics**: latency, query volume, retrieval overlap, feedback score  

---

## ✅ Milestone Plan (Checklist)  

- **M1 – Infra up**: Docker Compose (Elasticsearch, PostgreSQL, Airflow, API, UI)  
- **M2 – Ingestion v1**: 200 docs indexed; reindex DAG idempotent  
- **M3 – Search v1**: BM25 UI live; baseline relevance evaluation
- **M4 – Semantic v2**: embeddings + hybrid retrieval improve NDCG
- **M6 – RAG alpha v3**: `/ask` endpoint returns cited answers; traces visible  
- **M7 – Rollout**: pilot with team; feedback loop enabled  

---

👉 This roadmap ensures that **each phase stands alone as a functional IR system**, while also showing the progression from classic **`Keywords search → semantic retrieval → modern RAG`**.  
