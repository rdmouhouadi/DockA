# 🏗️ DocKA — Infrastructure Architecture

This document describes the **infrastructure layer** of **DocKA**.

Its role is to provide a **reproducible runtime environment** for DocKA services
while remaining strictly **decoupled from business logic**.

> Infrastructure in DocKA is an **adapter layer**, not an intelligence layer.

---

## 🎯 Purpose of the Infrastructure Layer

The infrastructure layer is responsible for:

- Running DocKA services locally
- Wiring services together (networking, ports, DNS)
- Providing stateful dependencies (databases, search engine)
- Scheduling and monitoring ingestion jobs
- Enabling observability and debugging

It is **not responsible** for:
- document ingestion logic
- data processing
- retrieval or ranking
- AI reasoning or agents
- business rules

All logic lives outside of `infra/`.

---

## 🧭 Core Design Principles

### 1️⃣ Infrastructure Is Replaceable

DocKA infrastructure must be easy to swap:

- Docker Compose → Kubernetes
- Local → Cloud
- Single-node → Distributed

No infrastructure decision should leak into the core codebase.

---

### 2️⃣ Containers Are the Unit of Deployment

Each major capability runs in its own container:

- API (FastAPI)
- UI (Streamlit)
- PostgreSQL
- Elasticsearch
- Airflow (webserver, scheduler, worker, triggerer)
- Redis (Celery broker)
- pgAdmin

This ensures isolation, reproducibility, and explicit contracts between services.

---

### 3️⃣ Two Isolated Databases, One PostgreSQL Instance

DocKA runs two logically separate databases on the same PostgreSQL server:

| Database | Purpose | Owner |
|----------|---------|-------|
| `docka_app` | Document metadata, application data | DocKA application |
| `docka_airflow` | Airflow internal metadata | Airflow only |

**Why two databases?**
- Prevents Airflow's internal tables from polluting the application schema
- Allows independent backups and restores
- Follows the principle of least privilege — the app never touches `docka_airflow`

The schema for `docka_app` is initialized via `postgres/01_init.sql`
on first container start.

---

### 4️⃣ Configuration via Environment Variables

All configuration is injected at runtime using environment variables.

Rules:
- No secrets in code
- No hardcoded endpoints
- `.env` files are never committed to git
- `.env.example` documents all required variables

---

### 5️⃣ Dev-First, Production-Oriented

The infrastructure is designed for learning, debugging, and iteration —
but structured so it can evolve naturally toward staging and production.

---

## 🗂️ Folder Structure

```bash
infra/
├── README.md                     # 📘 This document
│
├── docker/
│   ├── api.Dockerfile            # FastAPI container
│   ├── ui.Dockerfile             # Streamlit container
│   ├── airflow.Dockerfile        # Airflow container
│   └── airflow.requirements.txt  # Python deps for Airflow worker
│
├── elasticsearch/
│   └── mappings/
│       └── docs_v1.json          # Elasticsearch index mapping
│
├── postgres/
│   └── 01_init.sql               # DB creation + schema init
│
└── docker-compose.yml            # Local orchestration
```

---

## 🧱 Infrastructure Components

### 🔹 API Service (FastAPI)

**Container:** `api` — Port `8000`

**Purpose:**
- Expose DocKA search capabilities via HTTP
- Serve as the stable contract for the UI, future agents, and external integrations

**Responsibilities:**
- Request validation and parameter bounds checking
- Health check endpoint (`GET /health`)
- Calling the retrieval service
- Returning structured JSON responses

The API is **stateless** — it does not store data locally.
Interactive documentation is available at `http://localhost:8000/docs`.

---

### 🔹 UI Service (Streamlit)

**Container:** `ui` — Port `8501`

**Purpose:**
- Human-facing interface for search and document upload
- Internal demos and exploration

**Responsibilities:**
- Submit queries and display ranked results with snippets
- Upload documents (single file, multiple files, ZIP)
- Display ingested source tags and document counts
- System health check

The UI calls the ingestion pipeline **directly** for user uploads,
bypassing Airflow for immediate feedback.
For scheduled/batch ingestion, Airflow is used.

The UI contains **no business logic** beyond orchestrating these calls.

---

### 🔹 PostgreSQL (Metadata Store)

**Container:** `postgres` — Port `5432`

**Purpose:**
Source of truth for all document metadata and application state.

**Databases:**

`docka_app` — Application database:
```sql
CREATE TABLE documents (
    id         SERIAL PRIMARY KEY,
    doc_id     TEXT UNIQUE NOT NULL,
    source     TEXT NOT NULL,
    path       TEXT NOT NULL,
    title      TEXT,
    language   TEXT,
    checksum   TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);
```

`docka_airflow` — Airflow internal metadata (managed by Airflow, never touched by the app).

PostgreSQL is **not** used for search — only for metadata and idempotency enforcement.
pgAdmin is available at `http://localhost:5050` for database inspection.

---

### 🔹 Elasticsearch (Search Engine)

**Container:** `elasticsearch` — Port `9200`

**Purpose:**
- Keyword-based retrieval via BM25 (Phase 1)
- Hybrid retrieval via BM25 + vector search (Phase 2)

**Index:** `docka_documents`

**Key mapping decisions:**
- `content` — `text` type, standard analyzer — full-text search
- `title` — `text` type, boosted 3× at query time
- `path`, `checksum` — `keyword`, `index: false` — stored but not searchable
- `language` — `keyword` — filterable by language

Elasticsearch is a **disposable index** — it can be deleted and rebuilt
at any time by re-running the ingestion pipeline against PostgreSQL.

**Version:** Elasticsearch 8.12 — Python client pinned to `elasticsearch==8.12.0`.

---

### 🔹 Airflow (Scheduler)

**Containers:** `airflow-webserver`, `airflow-scheduler`, `airflow-worker`, `airflow-triggerer`
**Port:** `8088` (webserver UI)

**Purpose:**
- Schedule ingestion jobs
- Monitor pipeline execution
- Retry on failure

**Executor:** CeleryExecutor with Redis as the message broker.

**Version:** Airflow 2.10.4
*(Airflow 3.x was evaluated and rejected due to JWT authentication failures
in multi-container Docker setups — see `docs/troubleshooting.md` for details.)*

**Critical rule:**
> Airflow orchestrates pipelines but never contains ingestion logic.
> All logic must remain reusable outside Airflow.

---

### 🔹 Redis (Celery Broker)

**Container:** `redis` — Port `6379`

**Purpose:**
Message broker for Airflow's CeleryExecutor.
The scheduler publishes tasks to Redis; workers consume them.

Redis is an infrastructure concern only — the application never interacts with it directly.

---

### 🔹 pgAdmin (Database UI)

**Container:** `pgadmin` — Port `5050`

**Purpose:**
Web-based PostgreSQL administration interface for development and debugging.
Not used in production.

---

## 🔌 Networking Model

All services run on a private Docker bridge network named `docka`.

```
┌─────────────────────────────────────────────┐
│              Docker Network: docka           │
│                                             │
│  api ──────────────────────────► postgres   │
│  ui  ──────────────────────────► api        │
│  airflow-worker ───────────────► postgres   │
│  airflow-worker ───────────────► elasticsearch │
│  airflow-scheduler ────────────► redis      │
│  airflow-worker ───────────────► redis      │
└─────────────────────────────────────────────┘
```

- Services resolve each other via DNS (container name = hostname)
- PostgreSQL and Elasticsearch are **not exposed** to the host by default
- Only `api:8000`, `ui:8501`, `airflow-webserver:8088`, and `pgadmin:5050` are published

---

## 📦 Port Reference

| Service | Host Port | Purpose |
|---------|-----------|---------|
| Streamlit UI | 8501 | User interface |
| FastAPI | 8000 | Search API + health |
| Airflow | 8088 | Pipeline orchestration |
| Elasticsearch | 9200 | Search engine (dev only) |
| PostgreSQL | 5432 | Metadata store (dev only) |
| pgAdmin | 5050 | Database UI |
| Redis | 6379 | Celery broker (internal) |

---

## 💾 Volume Strategy

| Volume | Type | Purpose |
|--------|------|---------|
| `postgres_data` | Named volume | Persistent database storage |
| `elasticsearch_data` | Named volume | Persistent search index |
| `./data` → `/data` | Bind mount | Document storage (samples + uploads) |
| `./Ingestion` → `/opt/airflow/Ingestion` | Bind mount | Ingestion code in Airflow worker |

**Important:** Named volumes persist across `docker compose down`.
Use `docker compose down -v` to perform a full reset including data.

---

## 🚦 Infrastructure Roadmap

### M1 — Local Infrastructure Foundation ✅

Docker Compose setup with all services, private network, port exposure.

**Exit criteria:**
- `docker compose up --build` succeeds
- API reachable on `localhost:8000`
- UI reachable on `localhost:8501`
- PostgreSQL accessible via pgAdmin
- Containers restart cleanly

---

### M2 — Ingestion Runtime Support ✅

Airflow with CeleryExecutor, DAG discovery, volume mounts.

**Exit criteria:**
- Airflow UI accessible at `localhost:8088`
- DAGs trigger pipelines successfully
- Failures visible and debuggable in Airflow UI
- JSON-structured worker logs

---

### M3 — Two-Database Isolation ✅

Separate `docka_app` and `docka_airflow` databases on the same PostgreSQL instance.

**Exit criteria:**
- Application schema isolated from Airflow internal tables
- Independent backup and restore possible
- No cross-database contamination

---

### M4 — Observability Basics ⬜

Structured logs, health endpoints, basic service metrics.

**Exit criteria:**
- Issues diagnosable without guesswork
- Clear visibility into per-service behavior
- Health endpoint reports status of all dependencies

---

### M5 — Domain Portal Infrastructure ⬜ *(Phase 4)*

Infrastructure support for user-triggered web corpus ingestion.

**Scope:**
- Airflow DAG API exposure (trigger DAGs from the UI)
- Domain configuration table in `docka_app`
- Web source adapter containers (rate limiting, proxy)

---

### M6 — Production Hardening ⬜ *(Future)*

**Scope:**
- Resource limits per container
- Authentication for API and Airflow
- Externalized secrets management
- CI/CD integration

---

## 🧠 Relationship to DocKA Core

| Layer | Answers the question |
|-------|---------------------|
| Core | *What* happens |
| Pipelines | *In what order* |
| Infrastructure | *Where* and *when* |

Infrastructure answers only one question: **"Where does this run?"**

---

## 🏁 Summary

The infrastructure layer is intentionally:

- **Simple** — one `docker compose up` to start everything
- **Explicit** — every service and connection is declared
- **Replaceable** — Docker Compose can be swapped for Kubernetes without touching core logic
- **Boring by design** — predictability over cleverness

This is what allows **DocKA Core** to remain clean, testable, and future-proof.