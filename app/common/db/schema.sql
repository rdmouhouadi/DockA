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
