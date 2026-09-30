# RAG mit pgvector – Beispiel

Kleines, vollständiges Beispiel für semantische Suche (Retrieval) mit
PostgreSQL + pgvector, lokalen Embeddings ohne API-Schlüssel und einem
FastAPI-Dienst. Optional hängt ein LLM dran (RAG im engeren Sinn).

Was es zeigt:

- Text in Absätze zerlegen (Chunking), Embeddings berechnen, in Postgres speichern
- Vektorsuche mit Cosinus-Ähnlichkeit über einen HNSW-Index
- Tests gegen eine echte Postgres mit pgvector (testcontainers), TDD
- Docker Compose, Schema-Migration beim Start, Modell-Cache im Volume

## Starten

```sh
docker compose up --build
```

Beim ersten Start lädt die App das Embedding-Modell (ca. 220 MB) in das Volume
`modelle`; danach startet sie in wenigen Sekunden. Der Dienst läuft auf
http://localhost:8000, die interaktive API-Doku auf http://localhost:8000/docs.

## Beispiele

Dokument aufnehmen:

```sh
curl -s -X POST localhost:8000/dokumente \
  -H 'Content-Type: application/json' \
  -d '{"titel": "Alltag", "text": "Der Hund bellt im Garten.\n\nDie Steuererklärung ist bis Ende März fällig.\n\nDie Katze schläft auf dem Sofa."}'
```

```json
{"id": 1, "titel": "Alltag", "anzahl_absaetze": 3}
```

Semantisch suchen (die Frage enthält kein Wort aus dem Treffer):

```sh
curl -s 'localhost:8000/suche?q=Welches%20Tier%20macht%20L%C3%A4rm%3F&k=2'
```

```json
{"treffer": [
  {"titel": "Alltag", "absatz": "Der Hund bellt im Garten.", "score": 0.37},
  {"titel": "Alltag", "absatz": "Die Katze schläft auf dem Sofa.", "score": 0.06}
]}
```

Frage an ein LLM mit den Treffern als Kontext (nur wenn `LLM_BASE_URL` und
`LLM_API_KEY` gesetzt sind, sonst 503):

```sh
curl -s -X POST localhost:8000/frage \
  -H 'Content-Type: application/json' \
  -d '{"frage": "Welches Tier bellt?", "k": 3}'
```

## Aufbau

| Schritt | Umsetzung |
|---|---|
| Chunking | `app/chunking.py`: Leerzeilen trennen Absätze, überlange Absätze werden an Satzgrenzen geteilt (max. 1000 Zeichen) |
| Embedding | `app/embedding.py`: [fastembed](https://github.com/qdrant/fastembed) (ONNX, CPU) mit `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, 384 Dimensionen, ~50 Sprachen inkl. Deutsch. Vektoren werden normiert |
| Speichern | `app/db.py`, `sql/001_schema.sql`: Tabellen `dokumente` und `absaetze`, Spalte `embedding vector(384)`, psycopg 3 mit `pgvector.psycopg` |
| Index | `CREATE INDEX ... USING hnsw (embedding vector_cosine_ops)`: Approximate Nearest Neighbour, Standardparameter m=16, ef_construction=64 |
| Suche | `ORDER BY embedding <=> $frage LIMIT k`; `<=>` ist die Cosinus-Distanz, Score = `1 - Distanz` |
| Antwort | `app/llm.py`: austauschbarer Adapter, in Produktion jede OpenAI-kompatible Chat-API (OpenAI, Mistral, Ollama lokal), im Test eine Attrappe |

Endpunkte (`app/main.py`):

- `POST /dokumente` – `{"titel", "text"}` → `{"id", "titel", "anzahl_absaetze"}`
- `GET /suche?q=...&k=5` – `{"treffer": [{"titel", "absatz", "score"}]}`
- `POST /frage` – `{"frage", "k"}` → `{"antwort", "quellen"}`

## Tests

Die Tests starten per testcontainers einen echten `pgvector/pgvector`-Container;
Docker muss laufen. Das Embedding-Modell wird beim ersten Lauf nach
`~/.cache/fastembed` geladen.

```sh
uv sync
uv run pytest
```

Entstanden nach TDD: erst der Test, dann der Code. Die Tests decken Chunking,
Embedding (Dimension, Normierung, deutsche Semantik), Schema (Extension,
Tabellen, HNSW-Index, Idempotenz), Speichern und Suchen sowie die drei
Endpunkte inklusive LLM-Adapter mit `httpx.MockTransport` ab.

## Grenzen

Bewusst weggelassen, weil es ein Beispiel ist:

- kein Reranking, keine hybride Suche (BM25 + Vektor)
- keine Authentifizierung, kein Rate-Limit
- kein Verbindungspool, kein Löschen oder Aktualisieren von Dokumenten
- HNSW mit Standardparametern; `ef_search` und `m` sind nicht getunt
- Chunking ohne Überlappung und ohne Token-Zählung

## Lizenz

MIT, siehe `LICENSE`. Goran Strainovic, [Strainovic IT](https://strainovic-it.ch).
