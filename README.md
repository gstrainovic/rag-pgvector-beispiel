# Dokumente befragen – RAG-Demo mit pgvector

Eigene PDF-, Text- oder Markdown-Dateien hochladen und im Chat Fragen dazu stellen;
jede Antwort nennt die Absätze, auf die sie sich stützt. Läuft komplett lokal ohne
API-Schlüssel (Ollama) und lässt sich per Umgebungsvariable auf Mistral, OpenAI oder
jeden anderen OpenAI-kompatiblen Dienst umschalten.

**Live ausprobieren:** https://rag.strainovic-it.ch (läuft auf einer kleinen VM mit
Mistral als Modell; drei Beispieldokumente sind geladen, einfach fragen).

![Bildschirmfoto der Demo](docs/demo.png)

Stack: Next.js 16 (App Router, React 19, TypeScript strict, Tailwind CSS 4, shadcn/ui),
FastAPI (Python), PostgreSQL mit pgvector, Ollama, Docker Compose. Retrieval-Augmented
Generation (RAG) ohne Framework, damit jeder Schritt sichtbar bleibt.

## Architektur

Drei Dienste hintereinander: `web` (Next.js) → `api` (FastAPI) → `db` (PostgreSQL mit
pgvector); der Browser spricht nur mit `web`. Die Startseite ist eine Server Component, die
Modell-Info, Dokumentliste und Beispieldateien direkt bei der API holt und fertiges HTML
liefert; interaktiv sind nur zwei Client Components (Dokumente, Chat), das Löschen läuft als
Server-Aktion. Alles unter `/api/*` reicht ein Route Handler als Strom an die API weiter
(`web/src/app/api/[...pfad]/route.ts`, Adresse zur Laufzeit aus `API_URL`), darum kommen
Uploads ohne Zwischenpuffer an und die Antwort auf `POST /api/frage` als Server-Sent Events
Stück für Stück beim Browser.

## Starten

Voraussetzungen: Docker mit Compose v2. Für die GPU das NVIDIA Container Toolkit; ohne GPU
den Block `gpus:` in `compose.yaml` löschen, dann rechnet Ollama auf der CPU.

```sh
git clone https://github.com/gstrainovic/rag-pgvector-beispiel.git
cd rag-pgvector-beispiel
docker compose up --build
```

Beim ersten Start lädt der Dienst `ollama-init` die Modelle (ca. 3.2 GB) in das Volume
`ollama` und meldet «Modelle bereit»; die API lädt danach die Beispieldokumente von selbst.
Dann http://localhost:3000 öffnen und fragen. Stoppen mit `docker compose down` (Daten und
Modelle bleiben in den Volumes). Die API-Doku steht unter http://localhost:8000/docs.

## Beispieldokumente

Drei fiktive Texte liegen in `app/beispiele/` (Hausordnung, Wartungsanleitung, FAQ) und
sind immer geladen: Die API legt sie beim Start an, falls sie fehlen. In der Liste stehen
sie oben, sind als «Beispiel» markiert und lassen sich nicht löschen. Zu jedem gibt es das
Original als PDF und Markdown («Original ansehen»), um Antworten gegenzuprüfen. Die PDFs
erzeugt `uv run python scripts/beispiel_pdfs.py` aus den Markdown-Dateien; sie sind
eingecheckt.

## Auf ein Cloud-Modell umschalten

Alle Dienste sprechen das OpenAI-Protokoll (Chat Completions mit Streaming, `/embeddings`).
`.env.example` nach `.env` kopieren, Variante wählen, dann ohne Ollama starten:

```sh
docker compose up --build db api web
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

## Grenzen der öffentlichen Demo

Die Demo läuft ohne Anmeldung, jede Frage und jeder Upload kostet beim Modell-Anbieter.
Besucher werden über ein anonymes Sitzungs-Cookie getrennt (`rag_sitzung`, zufällige
Kennung, 30 Tage): Jeder sieht, durchsucht und löscht nur die Beispiele plus die eigenen
Uploads. Ein neuer Browser oder ein privates Fenster ist ein neuer Besucher, darum gelten
zusätzlich Tagesgrenzen für alle zusammen. Uploads verfallen nach 24 Stunden.

| Variable | Standard | Wirkung |
|---|---|---|
| `LIMIT_FRAGEN_PRO_TAG` | 300 | alle Besucher zusammen, Zähler in der Datenbank, Tageswechsel nach UTC |
| `LIMIT_FRAGEN_PRO_MINUTE_IP` | 10 | je IP-Adresse (`X-Forwarded-For`, gesetzt von Caddy), im Arbeitsspeicher |
| `LIMIT_DOKUMENTE_PRO_SITZUNG` | 25 | eigene Dokumente je Besucher; Löschen schafft Platz |
| `LIMIT_ABSAETZE_PRO_DOKUMENT` | 200 | längere Dokumente werden vor dem Embedding abgelehnt |
| `LIMIT_UPLOADS_PRO_TAG` | 300 | alle Besucher zusammen |
| `LIMIT_LEBENSDAUER_STUNDEN` | 24 | danach werden Uploads gelöscht |
| `LLM_MAX_TOKENS` | 500 | Länge einer Antwort |

Fest im Code: Frage höchstens 500 Zeichen, höchstens 10 Absätze Kontext (`k`), Absatz
höchstens 1000 Zeichen, Datei höchstens 20 MB. Ist eine Grenze erreicht, antwortet die API
mit 429 und einer deutschen Meldung, die die Oberfläche als Hinweis zeigt. `GET /api/info`
nennt `fragen_heute`, `limit_fragen_pro_tag` und `uploads_heute` für einen Tagescheck von
aussen.

Grösste mögliche Tagesausgabe bei Mistral mit diesen Werten (Preise siehe «Gemessen»,
gerechnet mit 3 Zeichen je Token):

- Fragen: je Frage höchstens rund 3'700 Token Eingabe (10 Absätze, Frage, Systemprompt)
  und 500 Token Ausgabe, also 0.00086 $; 300 Fragen: **0.26 $**
- Uploads: je Dokument höchstens 200 × 1000 Zeichen, rund 67'000 Token, also 0.0067 $;
  300 Dokumente: **2.00 $**
- zusammen höchstens rund **2.30 $ pro Tag**; mit dem, was die Oberfläche tatsächlich
  schickt (4 Absätze, kurze Texte), sind 300 Fragen rund 5 Cent

Die letzte Sicherung liegt beim Anbieter: dort ein Ausgabenlimit für das Konto setzen. Lehnt
der Anbieter ab (402, 403 oder 429), zeigt die Demo «Monatskontingent beim Modell-Anbieter
erreicht» statt des rohen Fehlers.

Was die Demo mit Daten tut, steht für Besucher unter `/datenschutz`
(`web/src/app/datenschutz/page.tsx`); jede Aussage dort beschreibt den Code und gehört bei
Änderungen an Sitzung, Grenzen oder Protokollen mit angepasst.

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

Speicher der Container (`docker stats`): web 50 MB (80 MB nach drei Uploads von zusammen
45 MB), api 65 MB, db 30 MB, ollama 1.9 GB RAM (plus VRAM). Im Server-Betrieb mit Mistral
entfällt Ollama. `next build` braucht auf 2 Kernen 16 s mit 2 GB und 33 s mit 1.5 GB
Arbeitsspeicher; mit 1 GB läuft er nicht durch.

Kosten bei Mistral (Preisseite mistral.ai/pricing, Stand 1. Oktober 2026: Mistral Small 4
0.15 $ / 0.60 $ pro Million Token Eingabe / Ausgabe, mistral-embed 0.10 $ pro Million):
eine Frage mit vier Absätzen Kontext (ca. 700 Token Eingabe, 50 Token Antwort) kostet rund
0.00015 $, ein Dokument mit 30 Absätzen einbetten rund 0.0003 $. Tausend Fragen: 15 Cent.

## Aufbau

| Schritt | Umsetzung |
|---|---|
| Datei lesen | `app/dateien.py`: PDF per pypdf (Absätze aus dem Layout, sonst Seiten), TXT und MD als UTF-8; max. 20 MB |
| Chunking | `app/chunking.py`: Leerzeilen trennen Absätze, überlange Absätze werden an Satzgrenzen geteilt, notfalls an Wortgrenzen (max. 1000 Zeichen) |
| Embedding | `app/embedding.py`: `POST {base}/embeddings` (Ollama, Mistral, OpenAI), 32 Absätze je Anfrage, oder fastembed lokal; Vektoren normiert, Dimension per `EMBED_DIM` oder Probeanfrage |
| Speichern | `app/db.py`, `sql/001_schema.sql`: Tabellen `dokumente` (mit `sitzung`, NULL = Beispiel) und `absaetze`, `embedding vector(N)`, psycopg 3 |
| Index | HNSW mit `vector_cosine_ops`, Standardparameter; `hnsw.iterative_scan = strict_order`, weil die Suche nach Sitzung filtert |
| Suche | `WHERE sitzung IS NULL OR sitzung = $besucher ORDER BY embedding <=> $frage LIMIT k`, Score = 1 − Cosinus-Distanz |
| Antwort | `app/llm.py`: Chat Completions mit `stream: true`, deutscher Systemprompt (nur aus den Absätzen antworten, sonst sagen, dass es nicht in den Dokumenten steht, Sprache der Frage) |
| Sitzung und Grenzen | `app/main.py` (Cookie als ASGI-Middleware), `app/grenzen.py` (Tageszähler, Minutenfenster) |
| Oberfläche | `web/`: Next.js App Router; `app/page.tsx` (Server Component), `components/` (Client Components, shadcn/ui in `components/ui/`), `app/aktionen.ts` (Server-Aktion), `app/api/[...pfad]/route.ts` (Weiterleitung), marked + DOMPurify für die Antworten |

Endpunkte (`app/main.py`, alle unter `/api`, Doku unter `/docs`):

- `POST /dokumente/upload` – Multipart `dateien` (mehrere), → `[{id, titel, anzahl_absaetze}]`
- `POST /dokumente` – `{titel, text}` als JSON
- `GET /dokumente` – `[{id, titel, anzahl_absaetze, erstellt, beispiel}]`, Beispiele zuerst
- `DELETE /dokumente/{id}` – nur eigene; Beispiel → 403, fremdes Dokument → 404
- `GET /beispiele` – `[{titel, dateiname, groesse}]`; `GET /beispiele/{dateiname}` – Datei als Download
- `GET /suche?q=…&k=5` – nur Retrieval
- `POST /frage` – `{frage, k}` → Server-Sent Events: `quellen` (Liste mit Titel, Absatz, Score), dann `token` je Textstück, `fehler` bei Problemen, `ende`
- `GET /info` – Modell, Basis-URL, Embedder, Anzahl Dokumente, Zähler des Tages

## Tests

Backend gegen eine echte Postgres mit pgvector (testcontainers, Docker muss laufen);
LLM und Embedding-Dienst per `httpx.MockTransport`; der Upload-Test erzeugt die PDF mit
reportlab. Oberfläche mit Vitest und React Testing Library (jsdom), wie es die Next-Doku
für Unit-Tests beschreibt.

```sh
uv sync --all-extras && uv run pytest                    # 121 Tests
cd web && npm ci && npm test                             # 62 Tests
npm run typecheck && npm run lint && npm run build       # tsc --noEmit, ESLint, next build
```

Entwicklung ohne Docker-Build: `docker compose up db ollama ollama-init`, dann
`DATABASE_URL=postgresql://rag:rag@localhost:5432/rag uv run uvicorn --factory
app.main:app_aus_umgebung` und `cd web && npm run dev` (ohne `API_URL` spricht Next mit
`http://localhost:8000`; dafür in `compose.yaml` bei `db` und `ollama` die Ports
`5432:5432` und `11434:11434` öffnen).

## Was fehlt

- kein Reranking, keine hybride Suche (BM25 + Vektor), kein Chunk-Überlapp
- keine Anmeldung: die Sitzung ist ein Cookie, kein Konto
- ein Chat-Verlauf nur im Browser-Tab, keine Nachfragen mit Gesprächskontext
- PDF-Text nur aus Textebene (keine OCR für Scans)
- Kontext 2048 Token in Ollama: bei `k` über 5 und sehr langen Absätzen wird gekürzt
- HNSW mit Standardparametern

## Lizenz

MIT, siehe `LICENSE`. Goran Strainovic, [Strainovic IT](https://strainovic-it.ch).
