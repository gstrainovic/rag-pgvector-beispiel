# Dokumente befragen – RAG-Demo mit pgvector

Eigene PDF-, Text- oder Markdown-Dateien hochladen und im Chat Fragen dazu stellen;
jede Antwort nennt die Absätze, auf die sie sich stützt. Läuft komplett lokal ohne
API-Schlüssel (Ollama) und lässt sich per Umgebungsvariable auf Mistral, OpenAI oder
jeden anderen OpenAI-kompatiblen Dienst umschalten.

**Live ausprobieren:** https://rag.strainovic-it.ch (läuft auf einer kleinen VM mit
Mistral als Modell; «Beispieldokumente laden» klicken, dann fragen).

![Bildschirmfoto der Demo](docs/demo.png)

Stack: Vue 3 + PrimeVue (TypeScript, Vite), FastAPI (Python), PostgreSQL mit pgvector,
Ollama, Docker Compose. Retrieval-Augmented Generation (RAG) ohne Framework, damit jeder
Schritt sichtbar bleibt.

## Starten

Voraussetzungen: Docker mit Compose v2. Für die GPU das NVIDIA Container Toolkit; ohne GPU
den Block `gpus:` in `compose.yaml` löschen, dann rechnet Ollama auf der CPU.

```sh
git clone https://github.com/gstrainovic/rag-pgvector-beispiel.git
cd rag-pgvector-beispiel
docker compose up --build
```

Beim ersten Start lädt der Dienst `ollama-init` die Modelle (ca. 3.2 GB) in das Volume
`ollama` und meldet «Modelle bereit». Danach: http://localhost:8000 öffnen,
«Beispieldokumente laden» klicken, Frage stellen. Stoppen mit `docker compose down`
(Daten und Modelle bleiben in den Volumes).

## Auf ein Cloud-Modell umschalten

Alle Dienste sprechen das OpenAI-Protokoll (Chat Completions mit Streaming, `/embeddings`).
`.env.example` nach `.env` kopieren, Variante wählen, dann ohne Ollama starten:

```sh
docker compose up --build db api
```

| Variable | lokal (Standard) | Mistral | OpenAI |
|---|---|---|---|
| `LLM_BASE_URL` | `http://ollama:11434/v1` | `https://api.mistral.ai/v1` | `https://api.openai.com/v1` |
| `LLM_API_KEY` | `ollama` (wird ignoriert) | Schlüssel | Schlüssel |
| `LLM_MODEL` | `qwen3:4b-instruct-2507-q4_K_M` | `mistral-small-latest` | `gpt-4o-mini` |
| `EMBED_PROVIDER` | `ollama` | `openai` | `openai` |
| `EMBED_MODEL` | `qwen3-embedding-cpu` | `mistral-embed` | `text-embedding-3-small` |
| `EMBED_DIM` | 1024 | 1024 | 1536 |

`EMBED_PROVIDER=fastembed` rechnet Embeddings im API-Container auf der CPU (384
Dimensionen, Image mit `--build-arg EXTRAS=fastembed` bauen). `LLM_REASONING_EFFORT=none`
schaltet bei Hybridmodellen wie `qwen3:4b` das Denken ab; bei Instruct-2507 nicht nötig.

Die Vektordimension steht im Schema. Wer den Embedder bei vorhandenen Daten wechselt,
bekommt beim Start eine klare Fehlermeldung und löscht die Daten mit
`docker compose down -v` (das Ollama-Volume gleich mit; wer es behalten will:
`docker volume rm rag-pgvector-beispiel_pgdata`).

Server-Betrieb mit Caddy und Let's Encrypt: `deploy/README.md`.

## Gemessen

Laptop mit Intel i7-8850H (12 Threads), 46 GB RAM, NVIDIA Quadro P1000 mit 4 GB VRAM,
Ollama 0.21 im Container, Oktober 2026. Fünf Fragen an die drei Beispieldokumente
(28 Absätze), `k=4`.

| | Qwen3-4B-Instruct-2507 Q4_K_M | gemma4:e2b |
|---|---|---|
| Generierung | **14.1 Token/s** | 24.0 Token/s |
| Prompt-Verarbeitung | 160 Token/s | 183 Token/s |
| Zeit bis zum ersten Token (warm) | **1.3–1.9 s** | 11–14 s |
| Antwort gesamt | 1.9–3.6 s | 12–14 s |
| Erste Frage nach dem Start (Modell laden) | ca. 6 s | – |
| VRAM mit Kontext 2048 | 2.9 GB | – |
| Antworten richtig, Ablehnung bei fehlendem Wissen, Englisch auf Englisch | 5/5 | 5/5 |

Qwen3-4B ist Standard: schneller bis zum ersten Token, bleibt dauerhaft im VRAM.

Embedder (28 Absätze einbetten, Top-1-Treffer bei zehn Testfragen):

| | qwen3-embedding:0.6b auf CPU | fastembed MiniLM-L12 (CPU) |
|---|---|---|
| Dimensionen | 1024 | 384 |
| 28 Absätze | 7.4 s | 0.5 s |
| eine Frage | ca. 100 ms | 6 ms |
| Top-1 richtig | **9/10** | 8/10 |

Warum der Embedder auf der CPU läuft: auf der GPU reserviert Ollama für
`qwen3-embedding:0.6b` 2.1 GB; zusammen mit dem Chat-Modell passt das nicht in 4 GB, und
Ollama tauscht dann bei jeder Frage die Modelle (gemessen 12 s pro Wechsel). Die
CPU-Variante entsteht aus `ollama/Modelfile.qwen3-embedding-cpu` (`num_gpu 0`); der
Init-Container legt sie an. Auf einer GPU mit 8 GB oder mehr kann `EMBED_MODEL` auf
`qwen3-embedding:0.6b` gesetzt werden.

Speicher der Container (`docker stats`): api 65 MB, db 30 MB, ollama 1.9 GB RAM
(plus VRAM). Im Server-Betrieb mit Mistral entfällt Ollama.

Kosten bei Mistral (Preisseite mistral.ai/pricing, Stand 1. Oktober 2026: Mistral Small 4
0.15 $ / 0.60 $ pro Million Token Eingabe / Ausgabe, mistral-embed 0.10 $ pro Million):
eine Frage mit vier Absätzen Kontext (ca. 700 Token Eingabe, 50 Token Antwort) kostet rund
0.00015 $, ein Dokument mit 30 Absätzen einbetten rund 0.0003 $. Tausend Fragen: 15 Cent.

## Aufbau

| Schritt | Umsetzung |
|---|---|
| Datei lesen | `app/dateien.py`: PDF per pypdf (Seiten als Absätze), TXT und MD als UTF-8; max. 20 MB |
| Chunking | `app/chunking.py`: Leerzeilen trennen Absätze, überlange Absätze werden an Satzgrenzen geteilt (max. 1000 Zeichen) |
| Embedding | `app/embedding.py`: `POST {base}/embeddings` (Ollama, Mistral, OpenAI) oder fastembed lokal; Vektoren normiert, Dimension per `EMBED_DIM` oder Probeanfrage |
| Speichern | `app/db.py`, `sql/001_schema.sql`: Tabellen `dokumente` und `absaetze`, `embedding vector(N)`, psycopg 3 |
| Index | HNSW mit `vector_cosine_ops`, Standardparameter |
| Suche | `ORDER BY embedding <=> $frage LIMIT k`, Score = 1 − Cosinus-Distanz |
| Antwort | `app/llm.py`: Chat Completions mit `stream: true`, deutscher Systemprompt (nur aus den Absätzen antworten, sonst sagen, dass es nicht in den Dokumenten steht, Sprache der Frage) |
| Oberfläche | `web/`: Vue 3, PrimeVue, marked + DOMPurify; die API liefert den Vite-Build aus |

Endpunkte (`app/main.py`, alle unter `/api`, Doku unter `/docs`):

- `POST /dokumente/upload` – Multipart `dateien` (mehrere), → `[{id, titel, anzahl_absaetze}]`
- `POST /dokumente` – `{titel, text}` als JSON
- `GET /dokumente` – `[{id, titel, anzahl_absaetze, erstellt}]`
- `DELETE /dokumente/{id}`
- `POST /beispiele` – lädt die drei fiktiven Texte aus `app/beispiele/`
- `GET /suche?q=…&k=5` – nur Retrieval
- `POST /frage` – `{frage, k}` → Server-Sent Events: `quellen` (Liste mit Titel, Absatz, Score), dann `token` je Textstück, `fehler` bei Problemen, `ende`
- `GET /info` – Modell, Basis-URL, Embedder, Anzahl Dokumente

## Tests

Backend gegen eine echte Postgres mit pgvector (testcontainers, Docker muss laufen);
LLM und Embedding-Dienst per `httpx.MockTransport`; der Upload-Test erzeugt die PDF mit
reportlab. Oberfläche mit Vitest und Vue Test Utils.

```sh
uv sync --all-extras && uv run pytest        # 59 Tests
cd web && npm ci && npm test                 # 20 Tests
```

Entwicklung ohne Docker-Build: `docker compose up db ollama ollama-init`, dann
`DATABASE_URL=postgresql://rag:rag@localhost:5432/rag uv run uvicorn --factory
app.main:app_aus_umgebung` und `cd web && npm run dev` (Vite leitet `/api` weiter).

## Grenzen

- kein Reranking, keine hybride Suche (BM25 + Vektor), kein Chunk-Überlapp
- keine Anmeldung, kein Rate-Limit: wer die Adresse kennt, kann Dokumente laden und löschen
- ein Chat-Verlauf nur im Browser-Tab, keine Nachfragen mit Gesprächskontext
- PDF-Text nur aus Textebene (keine OCR für Scans)
- Kontext 2048 Token in Ollama: bei `k` über 5 und sehr langen Absätzen wird gekürzt
- HNSW mit Standardparametern

## Lizenz

MIT, siehe `LICENSE`. Goran Strainovic, [Strainovic IT](https://strainovic-it.ch).
