-- Schema für das RAG-Beispiel. Wird beim Start der App ausgeführt, idempotent.
-- {dimension} wird von app/db.py durch die Vektordimension des Embedders ersetzt
-- (qwen3-embedding:0.6b und mistral-embed: 1024, fastembed MiniLM: 384).

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS dokumente (
    id          BIGSERIAL PRIMARY KEY,
    titel       TEXT NOT NULL,
    erstellt_am TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Anonyme Sitzung des Besuchers, der das Dokument hochgeladen hat (Cookie). NULL = Beispieldokument,
-- für alle sichtbar und nicht löschbar.
ALTER TABLE dokumente ADD COLUMN IF NOT EXISTS sitzung TEXT;
CREATE INDEX IF NOT EXISTS dokumente_sitzung ON dokumente (sitzung);

CREATE TABLE IF NOT EXISTS absaetze (
    id          BIGSERIAL PRIMARY KEY,
    dokument_id BIGINT NOT NULL REFERENCES dokumente(id) ON DELETE CASCADE,
    position    INTEGER NOT NULL,
    inhalt      TEXT NOT NULL,
    embedding   vector({dimension}) NOT NULL
);

-- HNSW-Index für Cosinus-Distanz (Operator <=>). Approximate Nearest Neighbour,
-- Standardparameter m=16, ef_construction=64.
CREATE INDEX IF NOT EXISTS absaetze_embedding_hnsw
    ON absaetze USING hnsw (embedding vector_cosine_ops);

-- Zähler je Tag (UTC) für die Grenzen der öffentlichen Demo: «fragen», «uploads».
CREATE TABLE IF NOT EXISTS tageszaehler (
    tag  DATE NOT NULL,
    name TEXT NOT NULL,
    wert INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (tag, name)
);
