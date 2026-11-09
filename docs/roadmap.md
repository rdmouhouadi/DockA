# 🗺️ DocKA — Roadmap

This document is the single source of truth for DocKA's development plan.  
It tracks every phase, every task, and the current status of each.

> **Legend:** ✅ Done · 🔄 In Progress · ⬜ Planned · 💤 Deferred

---

## Product Vision — Core + Verticals

DocKA is a knowledge retrieval platform built as **one core platform** with
**domain-specific verticals** on top. All of it lives in a single monorepo:

- **`core/`** — domain-agnostic ingestion, search, RAG, API and UI
- **`verticals/`** — domain extractors, pipelines and UIs built on the core

| Vertical | Domain | Status |
|----------|--------|--------|
| **DocKA Clinical** | Patient history retrieval with a Neo4j timeline | 🔄 Next — Month 2 |
| **DocKA Utility** | Smart metering asset history | ⬜ After DocKA Clinical |
| **DocKA Aviation MRO** | Aircraft maintenance history | ⬜ Roadmap |
| **DocKA Contracts** | Contract obligation retrieval | ⬜ Roadmap |

### Timeline

| Period | Scope | Release |
|--------|-------|---------|
| Done | Phase 1 — Keyword search POC | `v0.1.0` ✅ |
| Month 1 | Phase 2 — Semantic search | `v0.2.0` |
| Month 1 | Phase 3 — RAG with citations | `v0.3.0` |
| Month 2 | DocKA Clinical vertical | `v0.4.0-clinical` |

---

## Table of Contents

1. [Phase 1 — POC: Keyword Search](#phase-1--poc-keyword-search)
2. [Repository Restructure — Core + Verticals](#repository-restructure--core--verticals)
3. [Phase 2 — Semantic Search](#phase-2--semantic-search)
4. [Phase 3 — RAG with Citations](#phase-3--rag-with-citations)
5. [DocKA Clinical — First Vertical](#docka-clinical--first-vertical)
6. [Future Verticals](#future-verticals)
7. [Deferred — Domain Portal](#deferred--domain-portal)
8. [Locked Design Decisions](#locked-design-decisions)
9. [Cross-Cutting Concerns](#cross-cutting-concerns)

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

## Repository Restructure — Core + Verticals

**Goal:** Reorganise the repo so new domains are added as verticals on a shared core.  
**Status:** ✅ Complete

| Task | Status | Notes |
|------|--------|-------|
| Move `Ingestion/`, `app/`, `tests/` into `core/` | ✅ | `ingestion` lowercased to match imports (Linux-safe) |
| `verticals/clinical/` and `verticals/utility/` skeletons | ✅ | extractors, pipelines, ui (+ graph for clinical) |
| `core.Dockerfile` base image | ✅ | Verticals build `FROM` core |
| `clinical.Dockerfile` / `utility.Dockerfile` | ✅ | Stubs — dependencies added with each vertical |
| Split compose: core / clinical / full stack | ✅ | Shared via `include:`, each service defined once |

---

## Phase 2 — Semantic Search

**Goal:** Add semantic understanding to search via embeddings and hybrid retrieval.  
**Status:** ⬜ Planned — Month 1 · Release `v0.2.0`

**Why this matters:**  
BM25 finds exact keyword matches. Semantic search finds conceptually related content.  
A query for "water leak detection" should also find documents about "fuite d'eau"  
even if the exact words don't match.

---

### M1 — Document Chunking ✅

| Task | Status | Notes |
|------|--------|-------|
| Implement chunking module in `core/ingestion/` | ✅ | `chunker.py` — sliding window, 500 tokens, 50 overlap |
| Token counting with the embedding model's tokenizer | ✅ | `tokenizer.py` — e5 tokenizer, char offsets kept for citations |
| Store chunks in PostgreSQL | ✅ | `chunks` table linked to `documents` (created idempotently) |
| Update ingestion pipeline to chunk | ✅ | After the document row is written; re-runs backfill older documents |
| Stable `doc_id` across re-runs | ✅ | Reused by checksum — PostgreSQL, chunks and Elasticsearch share one id |
| Elasticsearch mapping applied | ✅ | `docs_v1.json` now loaded by `ensure_index()` |
| Chunk size evaluation | ⬜ | Moved to M4 — needs embeddings to measure retrieval quality |

---

### M2 — Embeddings ⬜

| Task | Status | Notes |
|------|--------|-------|
| Multilingual embedding model | ⬜ | `intfloat/multilingual-e5-base` (FR + EN, 512-token input — mpnet was trained at 128) |
| Add `sentence-transformers` dependency | ⬜ | |
| Embed chunks at ingestion time | ⬜ | Per-chunk embedding |
| Store vectors in Elasticsearch | ⬜ | `dense_vector` field type |

---

### M3 — Hybrid Retrieval ⬜

| Task | Status | Notes |
|------|--------|-------|
| Vector search | ⬜ | kNN search in Elasticsearch |
| Reciprocal Rank Fusion (RRF) | ⬜ | Combine BM25 + vector rankings |
| `GET /search?mode=hybrid` | ⬜ | Extend existing search endpoint |
| UI toggle: keyword vs hybrid | ⬜ | Streamlit radio button |

---

### M4 — Evaluation ⬜

| Task | Status | Notes |
|------|--------|-------|
| Build evaluation dataset | ⬜ | 20–30 query / relevant-doc pairs |
| NDCG@10 for BM25 | ⬜ | Phase 1 baseline |
| NDCG@10 for hybrid | ⬜ | Compared against baseline |
| Document results | ⬜ | In `docs/evaluation.md` |
| Tag `v0.2.0` | ⬜ | |

---

## Phase 3 — RAG with Citations

**Goal:** Answer questions with cited, verifiable responses grounded in the knowledge base.  
**Status:** ⬜ Planned — Month 1 · Release `v0.3.0`

**Why this matters:**  
Search returns documents. RAG returns answers.  
A user asking "how do I pair the iOTR device?" should get a direct answer  
with a citation pointing to the exact document and passage — and an explicit
"not found" when the knowledge base does not contain the answer.

---

### M1 — RAG Pipeline ⬜

| Task | Status | Notes |
|------|--------|-------|
| Local LLM via Ollama | ⬜ | Runs on-premise — no data leaves the machine |
| Retrieval → prompt → generate | ⬜ | Built on Phase 2 hybrid retrieval |
| Citation on every claim | ⬜ | Each statement linked to its source document |
| "Not found in the record" guardrail | ⬜ | Answer explicitly absent instead of hallucinating |
| `POST /ask` endpoint | ⬜ | Question → answer + sources |

---

### M2 — RAG Evaluation ⬜

| Task | Status | Notes |
|------|--------|-------|
| RAGAS evaluation | ⬜ | Faithfulness + answer relevance |
| "Not found" accuracy | ⬜ | Questions with no answer in the corpus |
| Document results | ⬜ | In `docs/evaluation.md` |
| Tag `v0.3.0` | ⬜ | |

---

### M3 — Stretch Goals ⬜

Previously planned for Phase 3; picked up if time allows.

| Task | Status | Notes |
|------|--------|-------|
| Streaming responses | ⬜ | Server-Sent Events |
| Langfuse tracing | ⬜ | Trace retrieval + generation steps |
| Latency monitoring | ⬜ | Per-step timing |
| User feedback collection | ⬜ | Thumbs up/down per answer |

---

## DocKA Clinical — First Vertical

**Goal:** Retrieve a patient's history across clinical documents, with a traversable
timeline graph and cited answers.  
**Status:** ⬜ Planned — Month 2 · Release `v0.4.0-clinical`  
**Location:** `verticals/clinical/` · `infra/docker/clinical.Dockerfile` · `infra/docker-compose.clinical.yml`

> **Synthetic data only.** Real patient data is never used.  
> **Text only** for the POC — no voice interface.

---

### Week 1 — Synthetic Data ⬜

| Task | Status | Notes |
|------|--------|-------|
| Generate synthetic patients | ⬜ | Synthea |
| Render French clinical documents | ⬜ | Referral letters, lab reports, discharge summaries |
| Scanned-image variants | ⬜ | Exercises the OCR path |

---

### Week 2 — Medical NLP + Neo4j Graph ⬜

| Task | Status | Notes |
|------|--------|-------|
| Clinical entity extraction | ⬜ | Diagnoses, medications, lab results, dates, allergies |
| OCR for scanned documents | ⬜ | `verticals/clinical/extractors/` |
| Neo4j graph schema | ⬜ | Nodes: Patient, Encounter, Medication, LabResult, Diagnosis, Allergy |
| Graph relationships | ⬜ | `HAS_LAB`, `PRESCRIBED`, `DIAGNOSED_WITH`, `ON_DATE` |
| Patient timeline as a traversable graph | ⬜ | `verticals/clinical/graph/` |

---

### Week 3 — Retrieval over Graph + Documents ⬜

| Task | Status | Notes |
|------|--------|-------|
| Queries combining Neo4j timeline + DocKA retrieval | ⬜ | Graph traversal + document passages |
| Citations on every answer | ⬜ | Reuses Phase 3 citation pipeline |
| Strict "not found" guardrail | ⬜ | No answer without a source |

---

### Week 4 — Demo + Evaluation ⬜

| Task | Status | Notes |
|------|--------|-------|
| Clinical Streamlit UI | ⬜ | Patient timeline view — `verticals/clinical/ui/` |
| Evaluation | ⬜ | Accuracy, citation correctness, "not found" accuracy |
| Demo video | ⬜ | 2 minutes |
| Write-up | ⬜ | Project summary and results |
| Tag `v0.4.0-clinical` | ⬜ | |

---

## Future Verticals

| Vertical | Scope | Status |
|----------|-------|--------|
| **DocKA Utility** | Smart metering asset history — `verticals/utility/` | ⬜ After DocKA Clinical |
| **DocKA Aviation MRO** | Aircraft maintenance history | ⬜ Roadmap |
| **DocKA Contracts** | Contract obligation retrieval | ⬜ Roadmap |

---

## Deferred — Domain Portal

**Status:** 💤 Deferred — superseded by the verticals strategy.  
Kept here for reference: web-based corpus acquisition may return as a core feature later.

| Milestone | Tasks |
|-----------|-------|
| Web Source Ingestion | `core/ingestion/sources/pubmed.py` (PubMed E-utilities), `web_crawler.py`, `ingest_web_source.py` pipeline, parameterised Airflow DAG |
| Domain Configuration | `domains` table (name, description, `fetch_config` JSONB), pre-configured + custom domains |
| Healthcare Demo Corpus | 1000–5000 PubMed abstracts, French HAS clinical guidelines, FR + EN corpus |
| Domain Portal UI | Domain selector, pipeline trigger from UI, corpus status, domain-scoped search |

---

## Locked Design Decisions

These are settled and should not be revisited without a strong reason.

| Decision | Rationale |
|----------|-----------|
| Airflow 2.10.4 (not 3.x) | JWT bug between components in multi-container Docker |
| Elasticsearch 8.12 + `elasticsearch==8.12.0` client | Client/server version match |
| PostgreSQL = source of truth, Elasticsearch = disposable index | Index can always be rebuilt |
| SHA-256 checksums | Idempotent ingestion |
| AGPL-3.0 license | Modifications stay open source |
| Monorepo — core + all verticals | Shared code, single CI, atomic changes |
| Neo4j for the Clinical timeline | Patient history is naturally a graph |
| Local LLM (Ollama) | No data leaves the machine |
| Voice interface | Out of scope for the Clinical POC |
| Kubernetes | Later — Docker Compose for now |

---

## Cross-Cutting Concerns

These tasks apply across all phases.

### Documentation

| Task | Status | Notes |
|------|--------|-------|
| Root `README.md` | ✅ | Vision, architecture, verticals, quick start |
| `docs/architecture.md` | ✅ | Components, data flow, repository layout |
| `docs/roadmap.md` | ✅ | This document |
| `docs/troubleshooting.md` | ✅ | All errors encountered + resolutions |
| `docs/learning-references.md` | ✅ | Curated learning material per concept |
| `core/ingestion/README.md` | ✅ | Ingestion architecture |
| `infra/README.md` | ✅ | Two-DB design, compose stacks |
| `docs/evaluation.md` | ⬜ | Phase 2+ search and RAG quality metrics |

### Data Control

DocKA's promise: *you decide what is stored and what is searchable.*

| Task | Status | Notes |
|------|--------|-------|
| Searchable lifetime — per-upload choice | ✅ | Temporary by default (1 h / 24 h / 7 days) or until removed |
| Expired content hidden from search on time | ✅ | `expires_at` filter in `/search` |
| Automatic purge of expired uploads | ✅ | `docka_purge_expired` DAG, every 15 minutes |
| Keep original files — per-upload choice | ✅ | Off by default; kept files in `data/uploads/<source>/` |
| UI states what will be stored, before upload | ✅ | Text, files, and for how long |
| `file_retained` recorded per document | ✅ | Sidebar shows `files kept` / `text only` |
| Remove a source | ✅ | Search index + PostgreSQL (chunks cascade) + kept files |
| Source tag validation | ✅ | Tags cannot escape `data/uploads/` |
| Remove a single document | ⬜ | Finer-grained than per source |

### Testing

| Task | Status | Notes |
|------|--------|-------|
| Unit tests — core modules | ✅ | 74 tests passing — `pytest` |
| Integration tests — API endpoints | ⬜ | Phase 2 |
| Search quality tests | ⬜ | Phase 2 evaluation |
| RAG evaluation | ⬜ | Phase 3 (RAGAS) |
| Clinical evaluation | ⬜ | Accuracy, citations, "not found" |

### GitHub

| Task | Status | Notes |
|------|--------|-------|
| `.gitignore` — clean repo | ✅ | `.env`, `.venv`, `__pycache__`, `data/`, local tool settings |
| `LICENSE` file — AGPL-3.0 | ✅ | |
| `.env.example` | ✅ | All required variables, incl. Neo4j |
| `CHANGELOG.md` | ✅ | Updated per release |
| Tag `v0.1.0` and publish | ✅ | |
