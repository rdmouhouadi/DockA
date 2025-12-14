# DocKA — Infrastructure & Platform Roadmap

This document tracks the **evolution of DocKA’s infrastructure and platform
architecture**, from early Proof of Concept (POC) to a production-ready system.

Its goal is to:
- Clarify what is **intentionally simple today**
- Document what is **expected to change**
- Preserve architectural intent over time

This roadmap complements `architecture.md` and focuses specifically on
**infrastructure, deployment, and platform-level concerns**.

---

## 1. Current State — POC Baseline (Phase 1)

The current DocKA infrastructure is designed to support:
- Local development
- Rapid experimentation
- Clear architectural learning

### ✅ What Is Already in Place

#### Containerization
- All core services are containerized using Docker:
  - PostgreSQL (metadata store)
  - Elasticsearch (keyword search)
  - Airflow (ingestion orchestration)
  - FastAPI (retrieval API)
  - Streamlit (user interface)

#### Orchestration
- `docker-compose.yml` orchestrates all services
- Single Docker network for simplicity
- Explicit port exposure for local debugging

#### Dependency Management
- Single `requirements.txt` at repository root
- Shared dependencies across API and UI
- Simple and transparent dependency resolution

> This choice is intentional for the POC phase to reduce cognitive overhead.

---

## 2. Intentional Simplifications (POC Constraints)

The following design choices are **deliberate trade-offs**, not omissions.

### Single-Node Services
- Elasticsearch runs in single-node mode
- PostgreSQL runs as a single instance
- Airflow runs in a simplified single-container setup

**Reason**
- Easier debugging
- Faster setup
- Lower operational complexity

---

### Shared Dependency File
- One `requirements.txt` for all services

**Reason**
- Minimize duplication
- Keep dependency management approachable during learning

---

### Local Executor for Airflow
- Airflow uses `LocalExecutor`

**Reason**
- Avoids Celery / message brokers
- Enough for ingestion workloads at POC scale

---

### No Secrets Management
- Credentials stored in environment variables
- No vault or secret rotation

**Reason**
- Not required for local POC
- Will be replaced later

---

## 3. Planned Infrastructure Evolutions

This section outlines **expected changes**, without committing to timelines.

---

### 3.1 Dependency Management

**Current**
- Single `requirements.txt`

**Future**
- Split by service:
  - `requirements/api.txt`
  - `requirements/ui.txt`
  - `requirements/ingestion.txt`

**Trigger**
- Diverging dependencies
- Faster build requirements
- Security or compliance constraints

---

### 3.2 Container Orchestration

**Current**
- Docker Compose (local only)

**Future**
- Kubernetes (optional)
- Helm charts for deployments

**Trigger**
- Multi-environment deployments
- Scaling ingestion or API independently

---

### 3.3 Ingestion Infrastructure

**Current**
- Single Airflow container
- LocalExecutor

**Future**
- Dedicated scheduler and workers
- External metadata database
- Optional message queues

**Trigger**
- Increased document volume
- Parallel ingestion requirements

---

### 3.4 Search & Retrieval Layer

**Current**
- Elasticsearch (BM25 only)

**Future**
- Vector database integration (Qdrant / Weaviate)
- Hybrid retrieval (BM25 + vectors)
- Retrieval evaluation pipelines

**Trigger**
- Phase 2 (semantic search)

---

### 3.5 API Layer

**Current**
- Single FastAPI service
- Stateless endpoints

**Future**
- Authentication middleware
- Rate limiting
- Agent orchestration endpoints

**Trigger**
- Multi-user access
- Support automation use cases

---

### 3.6 UI Layer

**Current**
- Streamlit UI

**Future**
- Role-based views
- Domain-specific UIs
- Alternative frontends (React, internal tools)

**Trigger**
- Wider adoption
- Different user personas

---

## 4. Observability & Operations

### Current
- Airflow UI
- Basic application logs
- Elasticsearch profiling tools

### Future
- Centralized logging
- Metrics dashboards
- Distributed tracing (Langfuse / OpenTelemetry)

---

## 5. What Will *Not* Change

Some architectural decisions are considered **stable**:

- Separation of ingestion and retrieval
- Elasticsearch as a disposable index
- PostgreSQL as metadata source of truth
- Stateless API services
- Platform-first design (DocKA Core)

These choices enable future extensions without redesign.

---

## 6. Relation to Support Use Cases

This infrastructure roadmap explicitly prepares DocKA for:
- Technical support ticket resolution
- AI-assisted troubleshooting
- Multi-solution smart metering support

Support-specific logic will be introduced as **modules on top of DocKA Core**,
without modifying this infrastructure baseline.

---

## 7. Summary

DocKA’s infrastructure is:
- **Simple by design**
- **Explicitly documented**
- **Intentionally evolvable**

This roadmap ensures that future changes remain
architecturally consistent and justifiable.
