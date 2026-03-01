# 📋 DocKA — Changelog

All notable changes to DocKA are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [v0.1.0] — 2026-03-01

### 🎉 First Release — Phase 1 POC Complete

This release marks the completion of Phase 1 — a fully working end-to-end
keyword search system on a real document corpus.

---

### Added

**Infrastructure**
- Docker Compose setup with 9 services: PostgreSQL, Elasticsearch, Airflow (webserver, scheduler, worker, triggerer), Redis, FastAPI, Streamlit, pgAdmin
- Two isolated PostgreSQL databases: `docka_app` (application) and `docka_airflow` (Airflow internal)
- Private Docker bridge network with DNS-based service discovery
- Elasticsearch 8.12 with explicit `docka_documents` index mapping
- Airflow 2.10.4 with CeleryExecutor and Redis broker

**Ingestion Core**
- `checksum.py` — SHA-256 content hashing for idempotency (8KB chunk streaming)
- `normalizer.py` — 6-step text normalization pipeline (unicode, control chars, page numbers, whitespace)
- `repository.py` — PostgreSQL persistence with `ON CONFLICT (checksum) DO NOTHING`
- `es_repository.py` — Elasticsearch indexing with idempotent index creation
- Language detection via `langdetect` — auto-detects FR, EN, and others
- UTC `created_at` timestamp on all documents

**Extractors**
- `pdf.py` — PDF text extraction via `pypdf`
- `docx.py` — Word document extraction via `python-docx`
- `html.py` — HTML extraction via `BeautifulSoup4` (strips tags, script, style)
- `txt.py` — Plain text extraction with UTF-8 / latin-1 fallback
- Extractor registry pattern — adding a new format requires one file + one line

**Pipelines**
- `ingest_folder.py` — full folder ingestion orchestrator
- `ingest_postgres.py` — single document → PostgreSQL sub-pipeline
- `ingest_elasticsearch.py` — single document → Elasticsearch sub-pipeline
- Airflow DAG: `ingest_documents` — scheduled filesystem ingestion

**Search API**
- `GET /search?q=...&size=...` — BM25 keyword search endpoint
- `multi_match` query with `title^3` boost and `fuzziness: AUTO`
- Highlighted snippets (2 fragments × 200 chars, `<em>` tags)
- `GET /health` — service health check endpoint
- Interactive API docs at `http://localhost:8000/docs`

**Streamlit UI**
- Search tab — query input, result count selector, ranked results with scores and snippets
- Upload tab — single file, multiple files, and ZIP archive support
- Source tagging — user-defined tag or filename default
- Sidebar — ingested sources with document counts (from PostgreSQL)
- System health check panel

**Tests**
- 32 unit tests across 6 test classes
- `TestFileChecksum` (6), `TestNormalizeText` (10), `TestDetectLanguage` (5)
- `TestTXTExtractor` (4), `TestHTMLExtractor` (4), `TestDOCXExtractor` (3)
- `conftest.py` for project root path setup
- All tests run without Docker, database, or Elasticsearch

**Documentation**
- `README.md` — project overview, vision, architecture, quick start, roadmap
- `docs/architecture.md` — full component and data flow documentation
- `docs/roadmap.md` — all phases and tasks with status tracking
- `docs/troubleshooting.md` — 12 errors documented with root causes and resolutions
- `docs/learning-references.md` — 15 concepts with curated learning resources
- `Ingestion/README.md` — updated ingestion architecture with new milestones
- `infra/README.md` — updated infrastructure documentation

---

### Technical Decisions

- **Airflow 2.10.4 over 3.x** — Airflow 3.x JWT authentication fails in multi-container Docker setups
- **Elasticsearch client pinned to 8.12.0** — client v9 is incompatible with server v8
- **Direct pipeline call from Streamlit for uploads** — bypasses Airflow for immediate user feedback
- **SHA-256 on raw bytes** — detects any file change, including metadata-only changes
- **AGPL-3.0 license** — allows open collaboration while protecting commercial use

---

### Known Limitations

- PDF extraction is text-layer only — scanned PDFs (image-only) return empty content
- Language detection unreliable on very short texts (< 50 characters)
- No authentication on any service — development environment only
- Single-node Elasticsearch (1 shard, 0 replicas) — not suitable for production

---

### What's Next — v0.2.0 (Phase 2)

- Document chunking
- Multilingual sentence embeddings
- Vector search in Elasticsearch
- Hybrid BM25 + vector retrieval with RRF fusion
- NDCG@10 evaluation against Phase 1 baseline

---

[v0.1.0]: https://github.com/rdmouhouadi/Docka/releases/tag/v0.1.0
