-- Schema für das RAG-Beispiel. Wird beim Start der App ausgeführt, idempotent.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS dokumente (
    id          BIGSERIAL PRIMARY KEY,
    titel       TEXT NOT NULL,
    erstellt_am TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 384 = Dimension von sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
CREATE TABLE IF NOT EXISTS absaetze (
    id          BIGSERIAL PRIMARY KEY,
    dokument_id BIGINT NOT NULL REFERENCES dokumente(id) ON DELETE CASCADE,
    position    INTEGER NOT NULL,
    inhalt      TEXT NOT NULL,
    embedding   vector(384) NOT NULL
);

-- HNSW-Index für Cosinus-Distanz (Operator <=>). Approximate Nearest Neighbour,
-- Standardparameter m=16, ef_construction=64.
CREATE INDEX IF NOT EXISTS absaetze_embedding_hnsw
    ON absaetze USING hnsw (embedding vector_cosine_ops);
