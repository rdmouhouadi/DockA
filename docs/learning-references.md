# 📚 DocKA — Learning References

This document maps every concept used in DocKA to the best learning resource available.

It is organized by phase, then by concept.
For each concept you will find:
- A plain-English explanation of what it is and why it matters in DocKA
- A single good resource to learn it deeply

> This is a living document. References will be added as new phases are built.

---

## Table of Contents

1. [Phase 1 — Foundations](#phase-1--foundations)
   - [Information Retrieval](#information-retrieval)
   - [BM25](#bm25)
   - [Inverted Index](#inverted-index)
   - [TF-IDF](#tf-idf)
   - [Text Normalization](#text-normalization)
   - [Idempotency](#idempotency)
   - [Content-Based Checksums (SHA-256)](#content-based-checksums-sha-256)
   - [Docker & Docker Compose](#docker--docker-compose)
   - [PostgreSQL](#postgresql)
   - [Elasticsearch](#elasticsearch)
   - [Apache Airflow](#apache-airflow)
   - [FastAPI](#fastapi)
   - [Streamlit](#streamlit)
   - [Unit Testing with pytest](#unit-testing-with-pytest)
   - [Language Detection](#language-detection)
2. [Phase 2 — Semantic Search](#phase-2--semantic-search-coming-soon)
3. [Phase 3 — RAG](#phase-3--rag-coming-soon)
4. [Phase 4 — Domain Portal](#phase-4--domain-portal-coming-soon)

---

## Phase 1 — Foundations

---

### Information Retrieval

**What it is:**
Information Retrieval (IR) is the science of finding relevant documents
in a large collection in response to a query.
It is the foundation of every search engine — from Google to Elasticsearch.

**Why it matters in DocKA:**
DocKA is fundamentally an IR system. Understanding IR gives you the vocabulary
and mental models to reason about search quality, ranking, and relevance —
concepts that matter in every phase of the project.

**Key concepts to understand:**
- The difference between precision (are the results relevant?) and recall (did we find all relevant results?)
- The document-query relevance problem
- How ranking algorithms decide which document comes first

**Best resource:**
📺 [Stanford CS276 — Introduction to Information Retrieval (Lecture 1)](https://www.youtube.com/watch?v=kNkCfaH2rxc)
*Stanford's full IR course. Lecture 1 covers the fundamentals clearly and rigorously.*

**Supporting resource:**
📖 [Introduction to Information Retrieval — Manning, Raghavan, Schütze (free online)](https://nlp.stanford.edu/IR-book/)
*The standard academic textbook on IR. Chapters 1-6 cover everything used in Phase 1.*

---

### BM25

**What it is:**
BM25 (Best Match 25) is the ranking algorithm used by Elasticsearch
to score how relevant a document is to a query.
It is an evolution of TF-IDF that adds document length normalization
and term frequency saturation.

**Why it matters in DocKA:**
Every search result in Phase 1 is ranked using BM25.
Understanding it explains why `X file` scores 1.43 for "bluetooth"
while `Y file` scores 0.68 — and how to improve ranking quality.

**Key concepts to understand:**
- Term frequency (TF) — how often does the query term appear?
- Inverse document frequency (IDF) — how rare is the term across all documents?
- Document length normalization — shorter documents with the same term count rank higher
- k1 and b parameters — how to tune BM25 for your corpus

**Best resource:**
📺 [BM25 — The Algorithm Behind Search (Arize AI)](https://www.youtube.com/watch?v=a3sg6MH5vig)
*Clear visual explanation of BM25 with worked examples. 15 minutes.*

**Supporting resource:**
📖 [Elasticsearch: The Definitive Guide — Relevance chapter](https://www.elastic.co/guide/en/elasticsearch/guide/current/relevance-intro.html)
*How Elasticsearch implements BM25 in practice, with examples you can run.*

---

### Inverted Index

**What it is:**
An inverted index is the core data structure that makes fast text search possible.
Instead of storing documents as-is, it stores a mapping from each word
to the list of documents that contain it.

**Why it matters in DocKA:**
When you search for "bluetooth" in DocKA, Elasticsearch doesn't read
all 10 documents — it looks up "bluetooth" in the inverted index and
instantly gets the list of matching document IDs.
Without an inverted index, full-text search would be impossibly slow.

**Key concepts to understand:**
- How documents are tokenized into terms
- How the index maps term → [doc1, doc2, ...]
- Why this structure makes search O(1) instead of O(n)

**Best resource:**
📺 [How Search Engines Work — Inverted Index Explained](https://www.youtube.com/watch?v=LHkPEKIbHXc)
*Visual walkthrough of inverted index construction and lookup. 10 minutes.*

---

### TF-IDF

**What it is:**
TF-IDF (Term Frequency — Inverse Document Frequency) is the predecessor to BM25.
It is the original mathematical framework for scoring document relevance.
BM25 is an improved version of TF-IDF.

**Why it matters in DocKA:**
Understanding TF-IDF first makes BM25 much easier to grasp.
The IDF component is why a rare term like "iOTR" scores higher than
a common term like "le" even if both appear the same number of times.

**Key concepts to understand:**
- TF: frequency of term in document
- IDF: log(N / df) where N is total documents and df is documents containing the term
- Why multiplying them gives a good relevance score

**Best resource:**
📺 [TF-IDF Explained Visually (StatQuest)](https://www.youtube.com/watch?v=OymqCnh_OdU)
*Josh Starmer's clear, visual explanation. 20 minutes. Best TF-IDF video available.*

---

### Text Normalization

**What it is:**
Text normalization is the process of transforming raw extracted text
into a clean, consistent form suitable for indexing and search.
It includes removing noise, standardizing whitespace, handling encoding, and more.

**Why it matters in DocKA:**
Raw PDF extraction produces messy text with page numbers, excessive whitespace,
and control characters. Without normalization, these artifacts appear in
Elasticsearch and degrade search quality.
`normalizer.py` implements a 6-step normalization pipeline.

**Key concepts to understand:**
- Unicode normalization (NFC vs NFD forms)
- Why control characters appear in PDF extraction
- The difference between normalization (cleaning) and stemming/lemmatization (linguistic processing)
- Why we don't do stemming in Phase 1 (Elasticsearch handles it via analyzers)

**Best resource:**
📺 [Text Preprocessing for NLP (Krish Naik)](https://www.youtube.com/watch?v=LHkPEKIbHXc)
*Practical walkthrough of all common text cleaning steps in Python.*

**Supporting resource:**
📖 [Python `unicodedata` documentation](https://docs.python.org/3/library/unicodedata.html)
*Official docs for the unicode normalization functions used in `normalizer.py`.*

---

### Idempotency

**What it is:**
An operation is idempotent if running it multiple times produces the same result
as running it once. In DocKA, this means ingesting the same document twice
never creates a duplicate.

**Why it matters in DocKA:**
Airflow DAGs retry on failure. Users may upload the same file twice.
Without idempotency, every retry or re-upload would create duplicate documents
in both PostgreSQL and Elasticsearch, corrupting the knowledge base.

**Key concepts to understand:**
- Why distributed systems need idempotency (retries, failures, network issues)
- Natural keys vs surrogate keys for idempotency
- `ON CONFLICT DO NOTHING` in PostgreSQL
- Using content hashes as natural idempotency keys

**Best resource:**
📺 [Idempotency in Distributed Systems (Hussein Nasser)](https://www.youtube.com/watch?v=IP-rGJKSZ3s)
*Clear explanation of idempotency with real-world distributed system examples.*

---

### Content-Based Checksums (SHA-256)

**What it is:**
A checksum is a fixed-size hash computed from a file's content.
SHA-256 always produces a 64-character hex string from any input.
The same content always produces the same checksum.
Different content (even a single byte changed) produces a completely different checksum.

**Why it matters in DocKA:**
The checksum is DocKA's idempotency key. Before ingesting any document,
DocKA checks if its checksum already exists in PostgreSQL.
If it does, the document is skipped. This prevents duplicates and
allows the pipeline to be re-run safely at any time.

**Key concepts to understand:**
- Hash functions vs encryption (one-way vs two-way)
- Why SHA-256 is collision-resistant for document-sized inputs
- Reading files in chunks (memory efficiency for large PDFs)
- Why we hash the raw bytes (before extraction), not the extracted text

**Best resource:**
📺 [SHA-256 Hash Algorithm Explained (Computerphile)](https://www.youtube.com/watch?v=DMtFhACPnTY)
*Clear explanation of how SHA-256 works internally. 10 minutes.*

---

### Docker & Docker Compose

**What it is:**
Docker packages applications into containers — isolated, reproducible environments
that run the same way on any machine.
Docker Compose orchestrates multiple containers as a single application,
defining their connections, ports, and shared volumes.

**Why it matters in DocKA:**
DocKA runs 9 services (PostgreSQL, Elasticsearch, Airflow scheduler,
Airflow worker, Airflow webserver, Airflow triggerer, Redis, FastAPI, Streamlit).
Docker Compose makes this reproducible with a single command: `docker compose up`.

**Key concepts to understand:**
- Container vs virtual machine
- Images vs containers
- Volumes (persistent storage)
- Networks (service-to-service communication)
- `docker-compose.yml` structure: services, volumes, networks
- Why services communicate via DNS names (not IP addresses) in Docker

**Best resource:**
📺 [Docker Tutorial for Beginners (TechWorld with Nana)](https://www.youtube.com/watch?v=3c-iBn73dDE)
*The best Docker introduction available. 3 hours but worth every minute.*

**Supporting resource:**
📺 [Docker Compose Tutorial (TechWorld with Nana)](https://www.youtube.com/watch?v=MVIcrmeV_6c)
*Focused on Docker Compose specifically. 1 hour.*

---

### PostgreSQL

**What it is:**
PostgreSQL is an open-source relational database.
It stores structured data in tables with rows and columns,
enforces constraints (UNIQUE, NOT NULL, PRIMARY KEY),
and supports ACID transactions.

**Why it matters in DocKA:**
PostgreSQL is the source of truth for document metadata.
It stores every document's `doc_id`, `path`, `checksum`, `language`,
and `created_at`. The `UNIQUE` constraint on `checksum` is what
enforces idempotency at the database level.

**Key concepts to understand:**
- Tables, rows, columns, primary keys
- UNIQUE constraints and what happens on conflict
- `ON CONFLICT DO NOTHING` vs `ON CONFLICT DO UPDATE`
- Connection management with `psycopg2`
- Why we use two databases (`docka_app` and `docka_airflow`)

**Best resource:**
📺 [PostgreSQL Tutorial for Beginners (freeCodeCamp)](https://www.youtube.com/watch?v=qw--VYLpxG4)
*Complete PostgreSQL course. Covers everything used in DocKA.*

---

### Elasticsearch

**What it is:**
Elasticsearch is a distributed search engine built on Apache Lucene.
It stores documents as JSON, builds inverted indexes automatically,
and exposes a REST API for indexing and searching.

**Why it matters in DocKA:**
Elasticsearch is the search layer. It stores the full text of every document
and ranks search results using BM25. The `docka_documents` index is
the engine behind every `/search` query.

**Key concepts to understand:**
- Index, document, field (equivalent to database, row, column)
- Mapping (schema definition for Elasticsearch)
- Analyzers (how text is tokenized before indexing)
- `multi_match` query
- `highlight` — how Elasticsearch returns matching text fragments
- Why `content.keyword` is ignored for long text fields
- Client version matching (client 8.x → server 8.x)

**Best resource:**
📺 [Elasticsearch Tutorial for Beginners (TechWorld with Nana)](https://www.youtube.com/watch?v=C3tlMqaNSaI)
*Best introduction to Elasticsearch concepts. Covers indexes, mappings, and queries.*

**Supporting resource:**
📖 [Elasticsearch Query DSL — Official Docs](https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl.html)
*Reference for all query types including `multi_match` and `highlight`.*

---

### Apache Airflow

**What it is:**
Apache Airflow is a workflow orchestration platform.
You define pipelines as Directed Acyclic Graphs (DAGs) in Python,
and Airflow schedules, executes, monitors, and retries them.

**Why it matters in DocKA:**
Airflow schedules the ingestion pipeline to run automatically.
Without Airflow, ingestion would require manual script execution.
With Airflow, you can set the pipeline to run nightly, monitor failures,
and configure automatic retries.

**Key concepts to understand:**
- DAG (Directed Acyclic Graph) — a workflow with tasks and dependencies
- Operators (PythonOperator, BashOperator, etc.)
- Executors (LocalExecutor vs CeleryExecutor)
- Why CeleryExecutor requires Redis as a message broker
- The difference between the scheduler, worker, and webserver
- Why Airflow 2.x was chosen over 3.x (see troubleshooting.md)

**Best resource:**
📺 [Apache Airflow Tutorial for Beginners (Astro)](https://www.youtube.com/watch?v=IH1-0hwFZRQ)
*Official Airflow tutorial. Covers DAGs, operators, and the UI clearly.*

**Supporting resource:**
📺 [Airflow Architecture Explained (Data with Marc)](https://www.youtube.com/watch?v=AHgxHHkBCmE)
*Explains the relationship between scheduler, worker, and executor. Essential for understanding CeleryExecutor.*

---

### FastAPI

**What it is:**
FastAPI is a modern Python web framework for building REST APIs.
It uses Python type hints for automatic validation and generates
interactive documentation (Swagger UI) automatically.

**Why it matters in DocKA:**
FastAPI exposes the `/search` endpoint that the Streamlit UI calls.
It validates query parameters, calls the retrieval service,
and returns structured JSON responses.

**Key concepts to understand:**
- Path operations (`@app.get`, `@app.post`)
- Query parameters and validation (`Query(...)`)
- Routers for organizing endpoints
- Automatic docs at `/docs`
- HTTPException for error responses
- The difference between synchronous and async endpoints

**Best resource:**
📺 [FastAPI Course for Beginners (freeCodeCamp)](https://www.youtube.com/watch?v=0sOvCWFmrtA)
*Complete FastAPI course covering everything used in DocKA and more.*

---

### Streamlit

**What it is:**
Streamlit is a Python library for building interactive web applications
without writing HTML, CSS, or JavaScript.
You write Python and Streamlit renders it as a web page.

**Why it matters in DocKA:**
Streamlit is the user-facing interface. It provides the search bar,
results display, file upload, and sidebar — all written in pure Python.

**Key concepts to understand:**
- `st.text_input`, `st.button`, `st.file_uploader`
- `st.columns` for layout
- `st.markdown` with `unsafe_allow_html=True` for custom styling
- `st.tabs` for multi-section UI
- `st.sidebar` for persistent navigation elements
- `st.metric` for KPI-style numbers
- Why Streamlit re-runs the entire script on every interaction

**Best resource:**
📺 [Streamlit Tutorial for Beginners (Data Professor)](https://www.youtube.com/watch?v=ZZ4B0QUHuNc)
*Best introductory Streamlit tutorial. Covers all components used in DocKA.*

---

### Unit Testing with pytest

**What it is:**
Unit testing is the practice of writing small, isolated tests that verify
a single function does exactly what it is supposed to do.
pytest is the standard Python testing framework.

**Why it matters in DocKA:**
DocKA has 32 unit tests covering the core ingestion logic.
These tests verify that checksums are deterministic, text normalization
works correctly, and extractors return valid output.
They catch regressions when code changes in future phases.

**Key concepts to understand:**
- Test isolation (no database, no Elasticsearch, no Docker)
- `tmp_path` fixture for temporary files in tests
- Test classes for grouping related tests
- `assert` statements
- Why we test pure functions first
- `conftest.py` for shared test configuration
- The difference between unit tests and integration tests

**Best resource:**
📺 [pytest Tutorial (Corey Schafer)](https://www.youtube.com/watch?v=bbp_849-RZ4)
*The clearest pytest introduction available. Covers everything used in DocKA's test suite.*

---

### Language Detection

**What it is:**
Language detection is the automatic identification of the natural language
of a piece of text. Given "Ce guide a pour but de vous assister",
a language detector returns "fr" (French).

**Why it matters in DocKA:**
Language detection tags each document with its language code.
In Phase 2, this will enable language-specific text analyzers in Elasticsearch
(French analyzer for French documents, English analyzer for English documents),
improving search quality for multilingual corpora.

**Key concepts to understand:**
- How language detection works (n-gram frequency profiles)
- Why short or numeric text cannot be detected
- The `langdetect` library and its non-deterministic behavior
- Why we return `None` gracefully instead of raising exceptions

**Best resource:**
📖 [langdetect Python library — GitHub](https://github.com/Mimino666/langdetect)
*The library used in DocKA. README explains usage and limitations clearly.*

**Supporting resource:**
📺 [How Language Detection Works (Computerphile)](https://www.youtube.com/watch?v=mI9LBQBKcjc)
*Explains the underlying n-gram model that powers language detection.*

---

## Phase 2 — Semantic Search *(coming soon)*

References will be added when Phase 2 is built. Concepts will include:

- Word embeddings (Word2Vec, GloVe)
- Sentence embeddings (SBERT, multilingual models)
- Cosine similarity
- Vector databases and approximate nearest neighbor search (ANN)
- Document chunking strategies
- Hybrid search and Reciprocal Rank Fusion (RRF)
- NDCG@10 evaluation metric

---

## Phase 3 — RAG *(coming soon)*

References will be added when Phase 3 is built. Concepts will include:

- Retrieval-Augmented Generation architecture
- Prompt engineering for RAG
- Hallucination and faithfulness
- RAGAS evaluation framework
- LLM observability with Langfuse
- Streaming responses (Server-Sent Events)

---

## Phase 4 — Domain Portal *(coming soon)*

References will be added when Phase 4 is built. Concepts will include:

- Web crawling and scraping
- PubMed E-utilities API
- Knowledge graphs and ontologies
- Domain-specific corpus curation

---

*Last updated: Phase 1 complete — v0.1.0*