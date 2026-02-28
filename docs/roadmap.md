# 🗺️ DocKA — Roadmap

This document is the single source of truth for DocKA's development plan.  
It tracks every phase, every task, and the current status of each.

> **Legend:** ✅ Done · 🔄 In Progress · ⬜ Planned

---

## Table of Contents

1. [Phase 1 — POC: Keyword Search](#phase-1--poc-keyword-search)
2. [Phase 2 — Semantic Search](#phase-2--semantic-search)
3. [Phase 3 — RAG](#phase-3--rag)
4. [Phase 4 — Domain Portal](#phase-4--domain-portal)
5. [Cross-Cutting Concerns](#cross-cutting-concerns)

---

## Phase 1 — POC: Keyword Search

**Goal:** Build a working end-to-end search system on a real document corpus.  
**Status:** ✅ Complete — tagged as `v0.1.0`

---

### M1 — Infrastructure Foundation ✅

| Task | Status | Notes |
|------|--------|-------|
| Docker Compose with all services | ✅ | PostgreSQL, Elasticsearch, Airflow, FastAPI, Streamlit, pgAdmin, Redis |
| Two isolated PostgreSQL databases | ✅ | `docka_app` (application) + `docka_airflow` (Airflow internal) |
| Elasticsearch with custom mapping | ✅ | `docka_documents` index with BM25-optimized field types |
| Private Docker network | ✅ | All services communicate via DNS (service names) |
| Environment variable configuration | ✅ | `.env` file, no secrets in code |
| pgAdmin for database inspection | ✅ | Accessible at `localhost:5050` |

---

### M2 — Ingestion Core ✅

| Task | Status | Notes |
|------|--------|-------|
| `loader.py` — directory scanner | ✅ | Extractor registry pattern |
| `checksum.py` — SHA-256 hashing | ✅ | Reads in 8KB chunks, memory-efficient |
| `normalizer.py` — text cleaning | ✅ | Unicode, control chars, page numbers, whitespace |
| `repository.py` — PostgreSQL persistence | ✅ | Idempotent via `ON CONFLICT (checksum) DO NOTHING` |
| `es_repository.py` — Elasticsearch indexing | ✅ | Idempotent via `doc_id` as ES document ID |
| Language detection | ✅ | `langdetect` — detects FR, EN, and others |
| `created_at` timestamp | ✅ | UTC ISO 8601 format |

---

### M3 — Format Extractors ✅

| Task | Status | Notes |
|------|--------|-------|
| `pdf.py` — PDF extraction | ✅ | `pypdf` — text layer extraction |
| `docx.py` — Word extraction | ✅ | `python-docx` — paragraph-based extraction |
| `html.py` — HTML extraction | ✅ | `BeautifulSoup4` — strips tags, script, style |
| `txt.py` — Plain text extraction | ✅ | UTF-8 with latin-1 fallback |

---

### M4 — Ingestion Pipelines ✅

| Task | Status | Notes |
|------|--------|-------|
| `ingest_postgres.py` — single doc → PostgreSQL | ✅ | Returns bool (inserted / skipped) |
| `ingest_elasticsearch.py` — single doc → ES | ✅ | Returns bool (indexed / skipped) |
| `ingest_folder.py` — folder orchestrator | ✅ | Calls both sub-pipelines per document |
| Ingestion summary logging (JSON) | ✅ | ingested / skipped / failed counts + duration |

---

### M5 — Airflow Scheduling ✅

| Task | Status | Notes |
|------|--------|-------|
| Airflow 2.10 CeleryExecutor setup | ✅ | Downgraded from 3.x due to JWT bug |
| `ingest_documents` DAG | ✅ | Triggers `ingest_folder` pipeline |
| DAG visible and triggerable in UI | ✅ | Airflow at `localhost:8088` |
| Worker logs visible in Airflow UI | ✅ | JSON-structured logs |

---

### M6 — Search API ✅

| Task | Status | Notes |
|------|--------|-------|
| `retrieval.py` — BM25 search service | ✅ | `multi_match`, `title^3` boost, `fuzziness: AUTO` |
| Highlighted snippets | ✅ | 2 fragments × 200 chars, `<em>` tags |
| `search.py` — FastAPI router | ✅ | `GET /search?q=...&size=...` |
| Input validation | ✅ | `min_length=1`, `size` bounded 1-100 |
| Error handling | ✅ | HTTP 500 with detail message |
| Elasticsearch version pinning | ✅ | `elasticsearch==8.12.0` (client/server version match) |

---

### M7 — Streamlit UI ✅

| Task | Status | Notes |
|------|--------|-------|
| Search tab with query input | ✅ | Result count selector (5, 10, 20) |
| Ranked results with scores | ✅ | BM25 score displayed per result |
| Highlighted snippets in UI | ✅ | Dark background for visibility |
| Language badge per result | ✅ | Shown if detected |
| File upload tab | ✅ | Single file, multiple files, ZIP |
| Source tag input | ✅ | User-defined or defaults to filename |
| Ingestion summary after upload | ✅ | ingested / skipped / failed metrics |
| Sidebar — ingested sources | ✅ | Source tag + document count from PostgreSQL |
| System health check | ✅ | API, PostgreSQL, Elasticsearch |

---

### M8 — Unit Tests ✅

| Task | Status | Notes |
|------|--------|-------|
| `TestFileChecksum` — 6 tests | ✅ | Determinism, sensitivity, format, edge cases |
| `TestNormalizeText` — 10 tests | ✅ | All cleaning steps verified |
| `TestDetectLanguage` — 5 tests | ✅ | FR, EN, empty, undetectable, return type |
| `TestTXTExtractor` — 4 tests | ✅ | UTF-8, latin-1, empty file |
| `TestHTMLExtractor` — 4 tests | ✅ | Tag stripping, script, style removal |
| `TestDOCXExtractor` — 3 tests | ✅ | Paragraphs, empty document |
| `conftest.py` — path setup | ✅ | Enables imports without install |
| Total: 32 tests passing | ✅ | `pytest tests/ -v` |

---

## Phase 2 — Semantic Search

**Goal:** Add semantic understanding to search via embeddings and hybrid retrieval.  
**Status:** ⬜ Planned

**Why this matters:**  
BM25 finds exact keyword matches. Semantic search finds conceptually related content.  
A query for "water leak detection" should also find documents about "fuite d'eau"  
even if the exact words don't match.

---

### M1 — Document Chunking ⬜

| Task | Status | Notes |
|------|--------|-------|
| Implement `app/common/chunking.py` | ⬜ | Sliding window with overlap |
| Chunk size evaluation | ⬜ | Test 256, 512, 1024 tokens |
| Store chunks in PostgreSQL | ⬜ | New `chunks` table linked to `documents` |
| Update ingestion pipeline to chunk | ⬜ | After normalization step |

---

### M2 — Embeddings ⬜

| Task | Status | Notes |
|------|--------|-------|
| Select multilingual embedding model | ⬜ | `paraphrase-multilingual-mpnet-base-v2` (FR+EN) |
| Add `sentence-transformers` dependency | ⬜ | |
| Embed chunks at ingestion time | ⬜ | Per-chunk embedding |
| Store vectors in Elasticsearch | ⬜ | `dense_vector` field type |

---

### M3 — Hybrid Retrieval ⬜

| Task | Status | Notes |
|------|--------|-------|
| Vector search endpoint | ⬜ | kNN search in Elasticsearch |
| Reciprocal Rank Fusion (RRF) | ⬜ | Combine BM25 + vector scores |
| `GET /search?mode=hybrid` | ⬜ | Extend existing search endpoint |
| UI toggle: keyword vs hybrid | ⬜ | Streamlit radio button |

---

### M4 — Evaluation ⬜

| Task | Status | Notes |
|------|--------|-------|
| Build evaluation dataset | ⬜ | 20-30 query/relevant-doc pairs |
| Compute NDCG@10 for BM25 | ⬜ | Baseline from Phase 1 |
| Compute NDCG@10 for hybrid | ⬜ | Compare against baseline |
| Document results | ⬜ | In `docs/evaluation.md` |

---

## Phase 3 — RAG

**Goal:** Answer questions with cited, verifiable responses grounded in the knowledge base.  
**Status:** ⬜ Planned

**Why this matters:**  
Search returns documents. RAG returns answers.  
A user asking "how do I pair the iOTR device?" should get a direct answer  
with a citation pointing to the exact document and passage.

---

### M1 — RAG Pipeline ⬜

| Task | Status | Notes |
|------|--------|-------|
| Select LLM (local or API) | ⬜ | Ollama (local) or OpenAI API |
| Implement retrieval → prompt → generate | ⬜ | LangChain or direct API |
| Citation extraction | ⬜ | Link answers to source documents |
| `POST /ask` endpoint | ⬜ | Question → answer + sources |
| Streaming responses | ⬜ | Server-Sent Events |

---

### M2 — RAG Evaluation ⬜

| Task | Status | Notes |
|------|--------|-------|
| RAGAS evaluation | ⬜ | Faithfulness + answer relevance |
| Hallucination detection | ⬜ | Flag answers not grounded in sources |
| Document results | ⬜ | In `docs/evaluation.md` |

---

### M3 — Observability ⬜

| Task | Status | Notes |
|------|--------|-------|
| Langfuse tracing integration | ⬜ | Trace retrieval + generation steps |
| Latency monitoring | ⬜ | Per-step timing |
| User feedback collection | ⬜ | Thumbs up/down per answer |

---

## Phase 4 — Domain Portal

**Goal:** Allow users to select a domain, trigger web-based corpus acquisition,  
and search over automatically fetched knowledge.  
**Status:** ⬜ Planned

**Why this matters:**  
This is the "domain knowledge acquisition" vision realized.  
A user selects "Healthcare" → DocKA fetches PubMed abstracts →  
builds the corpus → enables search and RAG over clinical literature.

---

### M1 — Web Source Ingestion ⬜

| Task | Status | Notes |
|------|--------|-------|
| `Ingestion/sources/pubmed.py` | ⬜ | PubMed E-utilities API |
| `Ingestion/sources/web_crawler.py` | ⬜ | Generic URL fetcher |
| `ingest_web_source.py` pipeline | ⬜ | Fetch → normalize → ingest |
| Airflow DAG for web ingestion | ⬜ | Parameterized: domain + query |

---

### M2 — Domain Configuration ⬜

| Task | Status | Notes |
|------|--------|-------|
| `domains` table in PostgreSQL | ⬜ | name, description, fetch_config (JSONB) |
| Pre-configured domains | ⬜ | Healthcare (PubMed), Telecom (smart metering) |
| Custom domain support | ⬜ | User-defined fetch config |

---

### M3 — Healthcare Demo Corpus ⬜

| Task | Status | Notes |
|------|--------|-------|
| Fetch 1000-5000 PubMed abstracts | ⬜ | Cardiology or oncology domain |
| French clinical guidelines (HAS) | ⬜ | haute-autorité-de-santé.fr |
| Multilingual corpus (FR + EN) | ⬜ | Language detection already in place |
| Pre-loaded in demo environment | ⬜ | Ready for a Demo |

---

### M4 — Domain Portal UI ⬜

| Task | Status | Notes |
|------|--------|-------|
| Domain selector in Streamlit | ⬜ | Healthcare · Telecom · Custom |
| Pipeline trigger from UI | ⬜ | Button → Airflow DAG trigger via API |
| Corpus status display | ⬜ | Document count, last updated |
| Domain switching | ⬜ | Search scoped to selected domain |

---

## Cross-Cutting Concerns

These tasks apply across all phases.

### Documentation ✅ / ⬜

| Task | Status | Notes |
|------|--------|-------|
| Root `README.md` | ✅ | Vision, architecture, quick start, roadmap |
| `docs/architecture.md` | ✅ | Full component and data flow documentation |
| `docs/roadmap.md` | ✅ | This document |
| `docs/troubleshooting.md` | ⬜ | All errors encountered + resolutions |
| `docs/learning-references.md` | ⬜ | Curated learning material per concept |
| `Ingestion/README.md` | ⬜ | Updated with pivot + new milestones |
| `infra/README.md` | ⬜ | Updated with two-DB design + domain portal |
| `docs/evaluation.md` | ⬜ | Phase 2+ search quality metrics |

### Testing ✅ / ⬜

| Task | Status | Notes |
|------|--------|-------|
| Unit tests — core modules | ✅ | 32 tests passing |
| Integration tests — API endpoints | ⬜ | Phase 2 |
| Search quality tests | ⬜ | Phase 2 evaluation |

### GitHub ⬜

| Task | Status | Notes |
|------|--------|-------|
| `.gitignore` — clean repo | ⬜ | Exclude `.env`, `.venv`, `__pycache__`, `data/` |
| `LICENSE` file — AGPL-3.0 | ⬜ | |
| `.env.example` | ⬜ | Document all required variables |
| `CHANGELOG.md` | ⬜ | v0.1.0 entry |
| Tag `v0.1.0` and publish | ⬜ | After documentation complete |