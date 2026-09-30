"""FastAPI-Dienst: Dokumente hochladen, semantisch suchen, Fragen streamen; liefert die Web-Oberfläche aus."""

import json
import logging
import os
from collections.abc import Iterator
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field, field_validator

from app import db
from app.chunking import in_absaetze
from app.dateien import ERLAUBTE_ENDUNGEN, MAX_BYTES, DateiFehler, text_aus_datei
from app.embedding import Embedder
from app.embedding import aus_umgebung as embedder_aus_umgebung
from app.llm import Antwortgeber
from app.llm import aus_umgebung as llm_aus_umgebung

log = logging.getLogger("rag")
BEISPIELE_ORDNER = Path(__file__).resolve().parent / "beispiele"
REPO_WURZEL = Path(__file__).resolve().parent.parent


class DokumentEingabe(BaseModel):
    titel: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1)

    @field_validator("text")
    @classmethod
    def text_nicht_leer(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Text darf nicht leer sein")
        return v


class DokumentAntwort(BaseModel):
    id: int
    titel: str
    anzahl_absaetze: int


class DokumentEintrag(DokumentAntwort):
    erstellt: datetime


class TrefferAntwort(BaseModel):
    titel: str
    absatz: str
    score: float


class SucheAntwort(BaseModel):
    treffer: list[TrefferAntwort]


class FrageEingabe(BaseModel):
    frage: str = Field(min_length=1)
    k: int = Field(default=5, ge=1, le=50)


class InfoAntwort(BaseModel):
    llm_modell: str
    llm_basis_url: str
    embedder: str
    anzahl_dokumente: int


def erstelle_app(
    datenbank_url: str,
    embedder: Embedder | None = None,
    antwortgeber: Antwortgeber | None = None,
    web_dist: Path | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.embedder = embedder or embedder_aus_umgebung()
        app.state.antwortgeber = antwortgeber or llm_aus_umgebung()
        db.migriere(datenbank_url, dimension=app.state.embedder.dimension)
        log.info("LLM %s @ %s, Embedder %s", app.state.antwortgeber.modell,
                 app.state.antwortgeber.basis_url, app.state.embedder.name)
        yield

    app = FastAPI(title="RAG mit pgvector – Demo", lifespan=lifespan)
    api = APIRouter(prefix="/api")

    def verbindung():
        with db.verbinde(datenbank_url) as conn:
            yield conn

    Conn = Annotated[db.psycopg.Connection, Depends(verbindung)]

    def _speichere(request: Request, conn, titel: str, text: str) -> DokumentAntwort:
        absaetze = in_absaetze(text)
        if not absaetze:
            raise HTTPException(422, f"«{titel}» enthält keinen lesbaren Text")
        embeddings = request.app.state.embedder.embed(absaetze)
        dok_id = db.speichere_dokument(conn, titel, absaetze, embeddings)
        return DokumentAntwort(id=dok_id, titel=titel, anzahl_absaetze=len(absaetze))

    @api.post("/dokumente", response_model=DokumentAntwort, status_code=201)
    def dokument_aufnehmen(eingabe: DokumentEingabe, request: Request, conn: Conn):
        return _speichere(request, conn, eingabe.titel, eingabe.text)

    @api.post("/dokumente/upload", response_model=list[DokumentAntwort], status_code=201)
    async def dokumente_hochladen(dateien: list[UploadFile], request: Request, conn: Conn):
        texte: list[tuple[str, str]] = []
        for datei in dateien:
            name = datei.filename or "datei"
            daten = await datei.read()
            if len(daten) > MAX_BYTES:
                raise HTTPException(413, f"«{name}» ist grösser als 20 MB")
            try:
                texte.append((name, text_aus_datei(name, daten)))
            except DateiFehler as e:
                status = 415 if "erlaubt" in str(e) else 422
                raise HTTPException(status, str(e)) from e
        # erst alle Dateien prüfen, dann alles in einer Transaktion speichern
        with conn.transaction():
            return [_speichere(request, conn, name, text) for name, text in texte]

    @api.get("/dokumente", response_model=list[DokumentEintrag])
    def dokumente_auflisten(conn: Conn):
        return [DokumentEintrag(**vars(d)) for d in db.liste_dokumente(conn)]

    @api.delete("/dokumente/{dok_id}", status_code=204, response_class=Response)
    def dokument_loeschen(dok_id: int, conn: Conn):
        if not db.loesche_dokument(conn, dok_id):
            raise HTTPException(404, "Dokument nicht gefunden")

    @api.post("/beispiele", response_model=list[DokumentAntwort], status_code=201)
    def beispiele_laden(request: Request, conn: Conn):
        ergebnis = []
        for pfad in sorted(BEISPIELE_ORDNER.glob("*.md")):
            titel = pfad.stem
            if db.titel_existiert(conn, titel):
                continue
            ergebnis.append(_speichere(request, conn, titel, pfad.read_text(encoding="utf-8")))
        return ergebnis

    @api.get("/suche", response_model=SucheAntwort)
    def suchen(
        request: Request,
        conn: Conn,
        q: Annotated[str, Query(min_length=1)],
        k: Annotated[int, Query(ge=1, le=50)] = 5,
    ):
        return SucheAntwort(treffer=_suche(request, conn, q, k))

    @api.post("/frage")
    def fragen(eingabe: FrageEingabe, request: Request, conn: Conn):
        antwortgeber: Antwortgeber = request.app.state.antwortgeber
        treffer = _suche(request, conn, eingabe.frage, eingabe.k)

        def events() -> Iterator[str]:
            yield _sse("quellen", [t.model_dump() for t in treffer])
            if not treffer:
                yield _sse("token", {"text": "Es sind noch keine Dokumente geladen. Bitte zuerst Dokumente hochladen oder die Beispieldokumente laden."})
            else:
                try:
                    for text in antwortgeber.antworte_stream(eingabe.frage, [t.absatz for t in treffer]):
                        yield _sse("token", {"text": text})
                except Exception as e:  # noqa: BLE001 – Fehler gehören in den Stream, nicht ins Log allein
                    log.exception("LLM-Fehler")
                    yield _sse("fehler", {"meldung": f"Das Sprachmodell hat nicht geantwortet: {e}"})
            yield _sse("ende", {})

        return StreamingResponse(
            events(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @api.get("/info", response_model=InfoAntwort)
    def info(request: Request, conn: Conn):
        return InfoAntwort(
            llm_modell=request.app.state.antwortgeber.modell,
            llm_basis_url=request.app.state.antwortgeber.basis_url,
            embedder=request.app.state.embedder.name,
            anzahl_dokumente=db.anzahl_dokumente(conn),
        )

    app.include_router(api)

    if web_dist and (web_dist / "index.html").is_file():
        # Gebaute Vue-App: echte Dateien direkt, alles andere (Routen der Single-Page-App) auf index.html
        @app.get("/{pfad:path}", include_in_schema=False)
        def web(pfad: str):
            datei = (web_dist / pfad).resolve()
            if pfad and datei.is_file() and web_dist.resolve() in datei.parents:
                return FileResponse(datei)
            return FileResponse(web_dist / "index.html")
    else:
        @app.get("/", include_in_schema=False)
        def wurzel():
            return {"hinweis": "Web-Oberfläche nicht gebaut. API-Doku unter /docs, Endpunkte unter /api."}

    return app


def _sse(event: str, daten: object) -> str:
    return f"event: {event}\ndata: {json.dumps(daten, ensure_ascii=False)}\n\n"


def _suche(request: Request, conn, q: str, k: int) -> list[TrefferAntwort]:
    (vektor,) = request.app.state.embedder.embed_query([q])
    return [TrefferAntwort(**vars(t)) for t in db.suche(conn, vektor, k)]


def app_aus_umgebung() -> FastAPI:
    logging.basicConfig(level=logging.INFO)
    web_dist = Path(os.environ.get("WEB_DIST", REPO_WURZEL / "web" / "dist"))
    return erstelle_app(os.environ["DATABASE_URL"], web_dist=web_dist)
