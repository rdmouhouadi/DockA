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
    checksum TEXT,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_documents_checksum ON documents(checksum);
CREATE INDEX IF NOT EXISTS idx_documents_doc_id ON documents(doc_id);