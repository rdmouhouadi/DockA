-- Application database
CREATE DATABASE docka_app;
GRANT ALL PRIVILEGES ON DATABASE docka_app TO docka;

-- Airflow metadata database
CREATE DATABASE docka_airflow;
GRANT ALL PRIVILEGES ON DATABASE docka_airflow TO docka;

-- Schema grants for Airflow
\c docka_airflow
GRANT ALL ON SCHEMA public TO docka;

-- Switch to docka_app and create application schema
\c docka_app
GRANT ALL ON SCHEMA public TO docka;

CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    doc_id TEXT UNIQUE NOT NULL,
    source TEXT NOT NULL,
    path TEXT NOT NULL,
    title TEXT,
    language TEXT,
    checksum TEXT UNIQUE NOT NULL,
    -- FALSE when an upload's original file was not kept (only extracted text remains)
    file_retained BOOLEAN NOT NULL DEFAULT TRUE,
    -- Temporary uploads: purged everywhere after this time (NULL = until removed)
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_documents_checksum ON documents(checksum);
CREATE INDEX IF NOT EXISTS idx_documents_doc_id ON documents(doc_id);
CREATE INDEX IF NOT EXISTS idx_documents_expires_at ON documents(expires_at) WHERE expires_at IS NOT NULL;
-- Chunks — Phase 2 (token-bounded passages of each document)
-- Same DDL as CHUNKS_DDL in core/ingestion/core/repository.py — keep in sync.
-- Existing databases get this table via ensure_schema() at ingestion time.
CREATE TABLE IF NOT EXISTS chunks (
    id SERIAL PRIMARY KEY,
    chunk_id TEXT UNIQUE NOT NULL,
    doc_id TEXT NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    start_char INT NOT NULL,
    end_char INT NOT NULL,
    token_count INT NOT NULL,
    created_at TIMESTAMP DEFAULT now(),
    UNIQUE (doc_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id);
