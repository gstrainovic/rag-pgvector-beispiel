# Demo auf einer kleinen VM betreiben

Ziel: `https://rag.strainovic-it.ch` auf einer Debian-VM mit 2 Kernen und 3.8 GB RAM,
ohne Ollama. Sprachmodell und Embeddings kommen von Mistral (`mistral-small-latest`,
`mistral-embed`), TLS von Let's Encrypt über Caddy.

Dienste in `docker-compose.server.yml`, alle mit `restart: unless-stopped`:

| Dienst | Aufgabe | Speicherlimit |
|---|---|---|
| `caddy` | TLS, einziger Dienst mit offenen Ports (80, 443), leitet an `web:3000` | 64 MB |
| `web` | Next.js (Oberfläche, reicht `/api/*` an die API weiter) | 256 MB |
| `api` | FastAPI, lädt beim Start die Beispieldokumente | 384 MB |
| `db` | PostgreSQL mit pgvector | 256 MB |

## Voraussetzungen

- Docker mit Compose v2 auf der VM, Ports 80 und 443 frei und von aussen erreichbar
- DNS: A-Record `rag.strainovic-it.ch` auf die IP der VM (im Infomaniak-Manager)
- Mistral-API-Schlüssel (console.mistral.ai), im Konto ein Ausgabenlimit gesetzt
- rund 1.5 GB freier Arbeitsspeicher für den Build (`free -m`): `next build` braucht auf
  2 Kernen gut eine halbe Minute, mit 1 GB läuft er nicht durch

## Einrichten

1. Code auf die VM kopieren. Auf der VM gibt es kein rsync, darum `tar` durch `ssh`. Vorher
   wird im Zielordner alles ausser der `.env` gelöscht, damit keine Dateien eines früheren
   Stands liegen bleiben (ein übrig gebliebenes `web/src/*.ts` bricht den Build):

   ```sh
   cd ~/projects/rag-pgvector-beispiel
   ssh debian@<VM-IP> 'mkdir -p /opt/rag-demo && find /opt/rag-demo -mindepth 1 -maxdepth 1 ! -name .env -exec rm -rf {} +'
   tar czf - --exclude=.git --exclude=.venv --exclude=node_modules --exclude=.next \
     --exclude=__pycache__ --exclude=.pytest_cache --exclude=.env . \
     | ssh debian@<VM-IP> 'tar xzf - -C /opt/rag-demo'
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

   Die Grenzen der Demo (`LIMIT_*`, `LLM_MAX_TOKENS`) haben Standardwerte und stehen nur in
   der `.env`, wenn sie abweichen sollen; siehe `.env.example` und das README im
   Hauptordner.

3. Bauen und starten (zwei Images: API mit Python, Oberfläche mit Node):

   ```sh
   cd /opt/rag-demo
   docker compose --env-file .env -f deploy/docker-compose.server.yml up -d --build
   docker compose --env-file .env -f deploy/docker-compose.server.yml logs -f api
   ```

   Die API meldet beim Start `LLM mistral-small-latest @ https://api.mistral.ai/v1,
   Embedder mistral-embed` und lädt die drei Beispieldokumente, falls sie fehlen. Caddy
   holt das Zertifikat, sobald der DNS-Eintrag zeigt.

4. Prüfen:

   ```sh
   curl -s https://rag.strainovic-it.ch/api/info
   curl -sN -X POST https://rag.strainovic-it.ch/api/frage \
     -H 'Content-Type: application/json' -d '{"frage":"Wann ist Nachtruhe?"}'
   ```

   `/api/info` nennt Modell, `fragen_heute`, `limit_fragen_pro_tag` und `uploads_heute`;
   die zweite Anfrage muss die Antwort Stück für Stück ausgeben, nicht am Ende auf einmal.

## Aktualisieren

Schritt 1 wiederholen, dann:

```sh
ssh debian@<VM-IP> 'cd /opt/rag-demo \
  && docker compose --env-file .env -f deploy/docker-compose.server.yml up -d --build --remove-orphans \
  && docker compose --env-file .env -f deploy/docker-compose.server.yml restart caddy'
```

`restart caddy` ist nötig, weil die Caddyfile als einzelne Datei eingebunden ist: der
laufende Container sieht eine ersetzte Datei erst nach dem Neustart.

Die Datenbank bleibt im Volume `deploy_pgdata`, die Zertifikate in `deploy_caddy_data`. Das
Schema zieht die API beim Start selbst nach. Dokumente ohne Sitzung, die kein
Beispieldokument sind, entfernt sie dabei: ohne Besitzer wären sie für alle sichtbar und
nicht löschbar.

Wer den Embedder wechselt (andere Dimension), muss die Daten löschen, ohne die Zertifikate
anzufassen:

```sh
cd /opt/rag-demo
docker compose --env-file .env -f deploy/docker-compose.server.yml down
docker volume rm deploy_pgdata
docker compose --env-file .env -f deploy/docker-compose.server.yml up -d
```

## Hinweise

- `.env` darf nie ins Repo; `deploy/` enthält nur Vorlagen.
- Die Demo hat keine Anmeldung. Besucher sind per Cookie getrennt, Grenzen pro Tag, pro
  Minute und IP und pro Besucher deckeln die Kosten (README im Hauptordner, Abschnitt
  «Grenzen der öffentlichen Demo»).
- Die Grenze je IP hängt an `X-Forwarded-For`. Caddy setzt den Header auf die Adresse des
  Besuchers und verwirft, was der Browser mitschickt; Next reicht ihn unverändert weiter.
  Darum darf ausser Caddy kein Dienst von aussen erreichbar sein.
- Protokolle: Caddy hat keine `log`-Direktive, uvicorn läuft mit `--no-access-log`, Next
  schreibt keine Zugriffe. Übrig bleiben Fehlermeldungen; die von Caddy enthalten die
  IP-Adresse der betroffenen Anfrage. Jeder Dienst behält höchstens 3 × 5 MB. So steht es
  in der Datenschutzerklärung der Demo (`/datenschutz`).
- Caddy leitet Server-Sent Events ungepuffert weiter (`flush_interval -1`) und weist
  Anfragen über 25 MB ab (`request_body`).
