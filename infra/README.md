# 🏗️ DocKA — Infrastructure Architecture

This document describes the **infrastructure layer** of **DocKA**.

Its role is to provide a **reproducible runtime environment** for DocKA services while remaining strictly **decoupled from business logic**.

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

- API
- UI
- PostgreSQL
- Elasticsearch
- Airflow

This ensures:
- isolation
- reproducibility
- explicit contracts between services

---

### 3️⃣ Configuration via Environment Variables

All configuration is injected at runtime using environment variables.

Rules:
- No secrets in code
- No hardcoded endpoints
- `.env` files are never committed
- `.env.example` documents required variables

---

## 🗂️ Folder Structure

```bash
infra/
├── README.md                 # 📘 This document
├── docker/
│   ├── api.Dockerfile        # FastAPI container
│   ├── ui.Dockerfile         # Streamlit container
│   └── airflow.Dockerfile    # Airflow container 
│
├── docker-compose.yml        # Local orchestration
```

---

### 4️⃣ Dev-First, Production-Oriented

The infrastructure is designed for:
- learning
- debugging
- iteration

But structured so it can evolve naturally toward:
- staging
- production

---

## 🧱 Infrastructure Components

### 🔹 API Service (FastAPI)

**Purpose**
- Expose DocKA Core capabilities via HTTP
- Serve as the stable contract for:
  - UI
  - future agents
  - external integrations

**Responsibilities**
- Request validation
- Health checks
- Calling DocKA Core services
- Returning structured responses

The API is **stateless** and does not store data locally.

---

### 🔹 UI Service (Streamlit)

**Purpose**
- Human-facing interface
- Debugging and exploration
- Internal demos

**Responsibilities**
- Submit queries
- Display results
- Visualize system behavior

The UI contains **no business logic**.

---

### 🔹 PostgreSQL (Metadata Store)

**Purpose**
- Source of truth for document metadata
- Enforce idempotency
- Store feedback and annotations (later phases)

**Typical data**
- document identifiers
- paths
- checksums
- titles
- languages
- timestamps

PostgreSQL is **not** used for search.

---

### 🔹 Elasticsearch (Search Engine)

**Purpose**
- Keyword-based retrieval (Phase 1)
- Hybrid retrieval later (Phase 2)

**Responsibilities**
- Indexing documents
- Ranking (BM25)
- Snippet generation

Elasticsearch complements PostgreSQL; it does not replace it.

---

### 🔹 Airflow (Scheduler)

**Purpose**
- Schedule ingestion jobs
- Monitor pipeline execution
- Retry on failure

**Critical rule**
> Airflow orchestrates pipelines, but never contains ingestion logic.

All logic must remain reusable outside Airflow.

---

## 🔌 Networking Model

All services run on a private Docker bridge network.

- Services resolve each other via DNS (service names)
- Databases are not exposed to the host
- Only API and UI ports are published

Examples:
- API → `postgres:5432`
- UI → `api:8000`
- Airflow → internal services only

---

## 🔐 Configuration & Secrets

Configuration is injected via environment variables such as:

- database connection parameters
- Elasticsearch endpoint
- runtime modes

Rules:
- No secrets committed
- `.env` files ignored by git
- `.env.example` documents required variables

---

## 🚦 Infrastructure Roadmap

### M1 — Local Infrastructure Foundation ✅

**Scope**
- Docker Compose setup
- API container
- UI container
- PostgreSQL
- Elasticsearch
- Private network
- Port exposure

**Exit Criteria**
- `docker compose up` succeeds
- API reachable on `localhost:8000`
- UI reachable on `localhost:8501`
- PostgreSQL accessible via pgAdmin
- Containers restart cleanly

---

### M2 — Ingestion Runtime Support ✅

**Scope**
- Airflow container
- DAG discovery
- Volume mounts for documents
- Centralized logs

**Exit Criteria**
- Airflow UI accessible
- DAGs trigger pipelines successfully
- Failures are visible and debuggable

---

### M3 — Observability Basics ⬜

**Scope**
- Structured logs
- Health endpoints
- Basic service metrics

**Exit Criteria**
- Issues can be diagnosed without guesswork
- Clear visibility into system behavior

---

### M4 — Production Hardening (Later) ⬜

**Scope**
- Resource limits
- Authentication
- Externalized storage
- CI/CD integration

---

## 🧠 Relationship to DocKA Core

| Layer | Responsibility |
|------|----------------|
| Core | What happens |
| Pipelines | In what order |
| Infrastructure | Where and when |

Infrastructure answers only one question:

> “Where does this run?”

---

## 🏁 Summary

The infrastructure layer is intentionally:

- simple
- explicit
- replaceable
- boring by design

This is what allows **DocKA Core** to remain clean, testable, and future-proof.