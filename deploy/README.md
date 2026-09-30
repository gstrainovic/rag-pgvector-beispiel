# Demo auf einer kleinen VM betreiben

Ziel: `https://rag.strainovic-it.ch` auf einer Debian-VM mit 2 Kernen und 3.8 GB RAM,
ohne Ollama. Sprachmodell und Embeddings kommen von Mistral (`mistral-small-latest`,
`mistral-embed`), TLS von Let's Encrypt über Caddy.

Dienste in `docker-compose.server.yml`: `db` (pgvector, 256 MB), `api` (FastAPI mit
gebauter Oberfläche, 384 MB), `caddy` (64 MB). Alle mit `restart: unless-stopped`.

## Voraussetzungen

- Docker mit Compose v2 auf der VM, Ports 80 und 443 frei und von aussen erreichbar
- DNS: A-Record `rag.strainovic-it.ch` auf die IP der VM (im Infomaniak-Manager)
- Mistral-API-Schlüssel (console.mistral.ai)

## Einrichten

1. Code auf die VM kopieren (ohne node_modules, .git, .venv):

   ```sh
   rsync -az --delete \
     --exclude node_modules --exclude .git --exclude .venv --exclude web/dist --exclude .env \
     ~/projects/rag-pgvector-beispiel/ debian@<VM-IP>:/opt/rag-demo/
   ```

2. Auf der VM die `.env` anlegen, nur für den Besitzer lesbar:

   ```sh
   ssh debian@<VM-IP>
   cat > /opt/rag-demo/.env <<'EOF'
   LLM_BASE_URL=https://api.mistral.ai/v1
   LLM_API_KEY=<Mistral-Schlüssel>
   LLM_MODEL=mistral-small-latest
   EMBED_PROVIDER=openai
   EMBED_MODEL=mistral-embed
   EMBED_DIM=1024
   POSTGRES_PASSWORD=<zufälliges Passwort>
   EOF
   chmod 600 /opt/rag-demo/.env
   ```

3. Bauen und starten (das Image baut die Vue-App mit Node und installiert die Python-
   Abhängigkeiten; erster Build 3–5 Minuten auf 2 Kernen):

   ```sh
   cd /opt/rag-demo
   docker compose -f deploy/docker-compose.server.yml up -d --build
   docker compose -f deploy/docker-compose.server.yml logs -f api
   ```

   Die API meldet beim Start `LLM mistral-small-latest @ https://api.mistral.ai/v1,
   Embedder mistral-embed`. Caddy holt das Zertifikat, sobald der DNS-Eintrag zeigt.

4. Prüfen:

   ```sh
   curl -s https://rag.strainovic-it.ch/api/info
   ```

## Aktualisieren

```sh
rsync ... (wie oben)
ssh debian@<VM-IP> 'cd /opt/rag-demo && docker compose -f deploy/docker-compose.server.yml up -d --build'
```

Die Datenbank bleibt im Volume `pgdata`. Wer den Embedder wechselt (andere Dimension),
muss die Daten löschen: `docker compose -f deploy/docker-compose.server.yml down -v`.

## Hinweise

- `.env` darf nie ins Repo; `deploy/` enthält nur Vorlagen.
- Die Demo hat keine Anmeldung. Wer die Adresse kennt, kann Dokumente hochladen und
  löschen und verursacht Mistral-Kosten (siehe README im Hauptordner, Abschnitt Kosten).
  Für eine öffentliche Demo empfiehlt sich `basic_auth` in der Caddyfile.
- Caddy leitet Server-Sent Events ungepuffert weiter (`flush_interval -1`), sonst käme
  die Antwort erst am Ende auf einmal.
