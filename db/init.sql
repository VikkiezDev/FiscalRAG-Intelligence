-- Runs automatically ONLY the first time the db volume is created.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
    id           SERIAL PRIMARY KEY,
    filename     TEXT NOT NULL UNIQUE,
    content_hash TEXT NOT NULL,
    ingested_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chunks (
    id          SERIAL PRIMARY KEY,
    document_id INT REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    page        INT,
    content     TEXT NOT NULL,
    embedding   VECTOR(384) NOT NULL
);

CREATE INDEX IF NOT EXISTS chunks_embedding_idx
    ON chunks USING hnsw (embedding vector_cosine_ops);

CREATE TABLE IF NOT EXISTS query_logs (
    id         SERIAL PRIMARY KEY,
    question   TEXT,
    answer     TEXT,
    chunk_ids  INT[],
    latency_ms INT,
    created_at TIMESTAMPTZ DEFAULT now()
);
