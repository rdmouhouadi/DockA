# 🔧 DocKA — Troubleshooting Log

This document is a honest record of every significant error encountered
while building DocKA, and exactly how each one was resolved.

It exists for two reasons:
1. **Practical** — if you hit the same error, you can find the fix immediately
2. **Educational** — understanding why something broke teaches more than tutorials

> Errors are ordered chronologically, grouped by component.

---

## Table of Contents

1. [Airflow](#airflow)
2. [PostgreSQL](#postgresql)
3. [Elasticsearch](#elasticsearch)
4. [Python / Dependencies](#python--dependencies)
5. [Docker](#docker)

---

## Airflow

---

### ❌ JWT Signature Verification Failure (Airflow 3.x)

**When:** Phase 1, initial Airflow setup  
**Severity:** Blocking — no tasks could execute

**Error message:**
```
jwt.exceptions.InvalidSignatureError: Signature verification failed
```

**Context:**
Airflow 3.x introduced a JWT-based authentication layer between the scheduler,
the execution API server, and the task workers. In a multi-container Docker setup
where each component runs in a separate container, token signing between containers
failed consistently regardless of configuration.

**What we tried:**
- Setting `AIRFLOW__CORE__EXECUTION_API_SERVER_URL` explicitly
- Matching `AIRFLOW__WEBSERVER__SECRET_KEY` across all containers
- Switching from LocalExecutor to CeleryExecutor in Airflow 3.x

None of these fixed the issue. The problem is architectural in Airflow 3.x's
multi-container JWT handling.

**Resolution:**
Downgraded from Airflow 3.x to **Airflow 2.10.4** with CeleryExecutor.

Key changes:
```dockerfile
# Before
FROM apache/airflow:3.1.7

# After
FROM apache/airflow:2.10.4
```

```yaml
# Removed in docker-compose.yml
AIRFLOW__CORE__EXECUTION_API_SERVER_URL: ...
AIRFLOW__CORE__AUTH_MANAGER: ...

# Service rename
airflow-apiserver → airflow-webserver
command: api-server → webserver
```

```python
# DAG import fix
# Before (Airflow 3.x)
from airflow.providers.standard.operators.python import PythonOperator

# After (Airflow 2.x)
from airflow.operators.python import PythonOperator
```

**Lesson:**
Always check if a new major version of infrastructure software has breaking
changes for your deployment model before upgrading. Airflow 3.x is stable
for single-process deployments but introduces complexity in distributed setups.

---

### ❌ Worker OOM Kill (SIGKILL -9)

**When:** Phase 1, first DAG runs  
**Severity:** Blocking — tasks killed mid-execution

**Error message:**
```
Process: Worker failed with SIGKILL -9
```

**Context:**
The Airflow worker container was killed by the OS out-of-memory killer
during PDF extraction. 32 parallel workers were configured by default,
each loading pypdf into memory simultaneously.

**Resolution:**
Reduced worker parallelism in `docker-compose.yml`:
```yaml
AIRFLOW__CORE__PARALLELISM: 4
AIRFLOW__CORE__MAX_ACTIVE_TASKS_PER_DAG: 2
```

**Lesson:**
Default Airflow parallelism settings assume a production server with significant RAM.
For local Docker development, always set explicit resource limits.

---

### ❌ DAG Not Visible in Airflow UI

**When:** Phase 1, after moving DAG files  
**Severity:** Minor — cosmetic issue

**Context:**
After reorganizing the folder structure, DAGs moved from
`Ingestion/airflow/dags/` but the volume mount in `docker-compose.yml`
still pointed to the old path.

**Resolution:**
Updated the volume mount in `docker-compose.yml`:
```yaml
volumes:
  - ./Ingestion/airflow/dags:/opt/airflow/dags
```

**Lesson:**
When renaming or moving folders, always check Docker volume mounts.
The container doesn't automatically follow filesystem changes on the host.

---

## PostgreSQL

---

### ❌ Database Not Found on First Start

**When:** Phase 1, infrastructure setup  
**Severity:** Blocking — all services failed to connect

**Error message:**
```
psycopg2.OperationalError: FATAL: database "docka" does not exist
```

**Context:**
The `01_init.sql` script creates `docka_app` and `docka_airflow` databases,
but the application code had `docka` hardcoded as the database name.

**Resolution:**
Updated all connection strings to use `docka_app`, and moved all credentials
to environment variables:
```python
conn = psycopg2.connect(
    host=os.getenv("POSTGRES_HOST", "postgres"),
    dbname=os.getenv("POSTGRES_DB", "docka_app"),
    user=os.getenv("POSTGRES_USER", "docka"),
    password=os.getenv("POSTGRES_PASSWORD", "docka")
)
```

**Lesson:**
Never hardcode database names. Use environment variables from day one —
even in a POC. The cost is one line of code and it prevents this entire class of error.

---

### ❌ ON CONFLICT Constraint Mismatch

**When:** Phase 1, after fixing idempotency logic  
**Severity:** Blocking — all inserts failed

**Error message:**
```
psycopg2.errors.InvalidColumnReference:
there is no unique or exclusion constraint matching the ON CONFLICT specification
```

**Context:**
The `repository.py` was updated to use `ON CONFLICT (checksum) DO NOTHING`
for idempotency, but the `documents` table in `01_init.sql` did not have
a `UNIQUE` constraint on the `checksum` column.

The table had:
```sql
checksum TEXT NOT NULL
```

But needed:
```sql
checksum TEXT UNIQUE NOT NULL
```

**Resolution:**
Updated `infra/postgres/01_init.sql` to add `UNIQUE` to the `checksum` column,
then ran a full reset:
```bash
docker compose down -v
docker compose up --build
```

**Lesson:**
The database schema and the application code must be kept in sync.
When changing `ON CONFLICT` targets in application code, always update
the corresponding constraint in the schema definition.

---

### ❌ Transaction Abort Cascade

**When:** Phase 1, same session as ON CONFLICT mismatch  
**Severity:** Blocking — all subsequent inserts in same session failed

**Error message:**
```
psycopg2.errors.InFailedSqlTransaction:
current transaction is aborted, commands ignored until end of transaction block
```

**Context:**
After the first insert failed with the constraint error above,
PostgreSQL put the transaction into an aborted state.
All subsequent insert attempts in the same connection failed with this error,
even though they were independent documents.

**Resolution:**
Fixed by resolving the root cause (constraint mismatch above).
The cascade was a symptom, not the cause.

**Lesson:**
In PostgreSQL, a single failed statement aborts the entire transaction.
Always fix the root error rather than trying to work around the cascade.
Consider adding `conn.rollback()` in error handlers to recover the connection:
```python
except Exception as e:
    conn.rollback()
    logger.error(...)
```

---

### ❌ Schema Not Applied on Fresh Start

**When:** Phase 1, after docker compose down -v  
**Severity:** Blocking — table did not exist

**Error message:**
```
psycopg2.errors.UndefinedTable: relation "documents" does not exist
```

**Context:**
Originally the application schema was in a separate `02_schema.sql` file
mounted as a second init script. After a volume reset, the mount path
was not correctly configured, so only `01_init.sql` ran.

**Resolution:**
Inlined the application schema directly into `01_init.sql`:
```sql
\c docka_app
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

Removed the separate `02_schema.sql` mount from `docker-compose.yml`.

**Lesson:**
Fewer init scripts = fewer mounting errors.
Keep the schema in one place unless there is a strong reason to split it.

---

## Elasticsearch

---

### ❌ Elasticsearch Client Version Mismatch

**When:** Phase 1, first search API call  
**Severity:** Blocking — all search requests returned 400

**Error message:**
```
BadRequestError(400, 'media_type_header_exception',
'Accept version must be either version 8 or 7, but found 9.
Accept=application/vnd.elasticsearch+json; compatible-with=9')
```

**Context:**
`pip install elasticsearch` installed version 9.x (the latest).
The Elasticsearch server running in Docker was version 8.12.
The Python client v9 sends `compatible-with=9` in request headers,
which the v8 server rejects.

**Resolution:**
Pinned the client version in both `requirements.txt` and `airflow.requirements.txt`:
```
elasticsearch==8.12.0
```

Then rebuilt all containers:
```bash
docker compose down
docker compose up --build
```

**Lesson:**
Always pin versions for infrastructure clients.
The Elasticsearch Python client follows the server version —
client 8.x talks to server 8.x, client 9.x talks to server 9.x.
This is documented but easy to miss if you `pip install` without constraints.

---

### ❌ Empty Elasticsearch Index Mapping

**When:** Phase 1, initial Elasticsearch setup  
**Severity:** Minor — search worked but without optimal field types

**Context:**
`infra/elasticsearch/mappings/docs_v1.json` was an empty file.
The index was created with Elasticsearch's default dynamic mapping,
which maps all text fields as both `text` and `keyword`.

This caused `_ignored` warnings for the `content` field:
```json
"_ignored": ["content.keyword"]
```

Long text fields cannot be indexed as `keyword` (Elasticsearch limit: 32766 bytes).

**Resolution:**
Wrote the explicit mapping with correct field types:
```json
{
  "mappings": {
    "properties": {
      "content": { "type": "text", "analyzer": "standard" },
      "path":    { "type": "keyword", "index": false },
      "checksum":{ "type": "keyword", "index": false }
    }
  }
}
```

Setting `"index": false` on `path` and `checksum` prevents them from being
searchable (unnecessary) while still storing them in the document source.

**Lesson:**
Always define explicit Elasticsearch mappings before indexing.
Dynamic mapping is convenient for exploration but causes
`_ignored` warnings and suboptimal field types in production.

---

## Python / Dependencies

---

### ❌ ModuleNotFoundError: No module named 'Ingestion'

**When:** Phase 1, running unit tests  
**Severity:** Blocking — no tests could run

**Error message:**
```
ModuleNotFoundError: No module named 'Ingestion'
```

**Context:**
`pytest` was run from the project root, but the project root was not
in `sys.path`. Python could not find the `Ingestion` package.

**Resolution:**
Created `conftest.py` at the project root:
```python
import sys
import os

sys.path.insert(0, os.path.abspath("."))
```

pytest automatically loads `conftest.py` before running tests,
making the project root importable.

**Lesson:**
For projects that are not installed as packages (`pip install -e .`),
`conftest.py` is the standard way to fix import paths in pytest.

---

### ❌ str = None Type Annotation Warning

**When:** Phase 1, writing unit tests  
**Severity:** Minor — IDE warning, not a runtime error

**Context:**
The function signature `def normalize_text(text: str) -> str` did not
accept `None`, but the test passed `None` to verify defensive behavior.
The IDE (VS Code) underlined `None` as a type error.

**Resolution:**
Updated the type hint to reflect the actual accepted input:
```python
# Before
def normalize_text(text: str) -> str:

# After
def normalize_text(text: str | None) -> str:
```

This is the Python 3.10+ union syntax. For Python 3.9 and below,
use `Optional[str]` from `typing`.

**Lesson:**
Type hints are contracts. If a function defensively handles `None`,
the type hint should say so. This makes the API explicit and prevents
IDE false positives in tests.

---

### ❌ langdetect Returns None for Short Numeric Text

**When:** Phase 1, language detection testing  
**Severity:** Minor — expected behavior, needed graceful handling

**Context:**
`langdetect.detect("123 456 789")` raises `LangDetectException`
because there is no detectable language in pure numeric input.

**Resolution:**
Wrapped the call in a try/except:
```python
from langdetect import detect, LangDetectException

def detect_language(text: str) -> str | None:
    try:
        return detect(text)
    except LangDetectException:
        return None
```

**Lesson:**
Language detection libraries raise exceptions on undetectable input.
Always wrap in try/except and return `None` rather than crashing
the ingestion pipeline over a single document.

---

## Docker

---

### ❌ UI Container Cannot Import Ingestion Package

**When:** Phase 1, file upload feature  
**Severity:** Blocking — upload tab crashed immediately

**Error message:**
```
ModuleNotFoundError: No module named 'Ingestion'
Traceback:
  File "/app/app/frontend/app_main.py", line 32, in <module>
    from Ingestion.pipelines.ingest_folder import ingest_folder
```

**Context:**
The UI Dockerfile only copied `app/frontend` and `app/common`.
When the upload feature was added, it imported `ingest_folder` directly
(to trigger ingestion without Airflow), but the `Ingestion` package
was not present in the UI container.

**Resolution:**
Added the `Ingestion` package to the UI Dockerfile:
```dockerfile
COPY app/frontend ./app/frontend
COPY Ingestion ./Ingestion        ← added
```

**Lesson:**
When a new import is added to application code, always check whether
the corresponding package is available in all containers that run that code.
The API, UI, and Airflow worker each have their own filesystem —
a package available in one is not automatically available in others.

---

### ❌ Volume Reset Required After Schema Change

**When:** Phase 1, multiple occasions after database changes  
**Severity:** Minor — predictable once understood

**Context:**
After changing `01_init.sql`, running `docker compose down` followed by
`docker compose up --build` did not apply the new schema.
The old schema persisted because the PostgreSQL data volume was not deleted.

**Resolution:**
Always use `-v` flag when a schema change requires a clean database:
```bash
docker compose down -v    # deletes volumes — full reset
docker compose up --build
```

Without `-v`:
```bash
docker compose down       # stops containers but keeps volumes
docker compose up --build # new schema NOT applied — old data persists
```

**Lesson:**
`docker compose down` and `docker compose down -v` are very different.
Use `-v` only when you intentionally want to wipe all persistent data.
In production, schema changes are handled with migrations (Alembic),
not volume resets.

---

*Last updated: Phase 1 complete — v0.1.0*