"""FastAPI-Dienst: Dokumente aufnehmen, semantisch suchen, optional fragen."""

import os
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator

from app import db
from app.chunking import in_absaetze
from app.embedding import Embedder, FastembedEmbedder
from app.llm import Antwortgeber, aus_umgebung


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


class TrefferAntwort(BaseModel):
    titel: str
    absatz: str
    score: float


class SucheAntwort(BaseModel):
    treffer: list[TrefferAntwort]


class FrageEingabe(BaseModel):
    frage: str = Field(min_length=1)
    k: int = Field(default=5, ge=1, le=50)


class FrageAntwort(BaseModel):
    antwort: str
    quellen: list[TrefferAntwort]


def erstelle_app(
    datenbank_url: str,
    embedder: Embedder | None = None,
    antwortgeber: Antwortgeber | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        db.migriere(datenbank_url)
        app.state.embedder = embedder or FastembedEmbedder()
        app.state.antwortgeber = antwortgeber
        yield

    app = FastAPI(title="RAG mit pgvector – Beispiel", lifespan=lifespan)

    def verbindung():
        with db.verbinde(datenbank_url) as conn:
            yield conn

    Conn = Annotated[db.psycopg.Connection, Depends(verbindung)]

    @app.post("/dokumente", response_model=DokumentAntwort, status_code=201)
    def dokument_aufnehmen(eingabe: DokumentEingabe, request: Request, conn: Conn):
        absaetze = in_absaetze(eingabe.text)
        embeddings = request.app.state.embedder.embed(absaetze)
        dok_id = db.speichere_dokument(conn, eingabe.titel, absaetze, embeddings)
        return DokumentAntwort(id=dok_id, titel=eingabe.titel, anzahl_absaetze=len(absaetze))

    @app.get("/suche", response_model=SucheAntwort)
    def suchen(
        request: Request,
        conn: Conn,
        q: Annotated[str, Query(min_length=1)],
        k: Annotated[int, Query(ge=1, le=50)] = 5,
    ):
        return SucheAntwort(treffer=_suche(request, conn, q, k))

    @app.post("/frage", response_model=FrageAntwort)
    def fragen(eingabe: FrageEingabe, request: Request, conn: Conn):
        antwortgeber = request.app.state.antwortgeber
        if antwortgeber is None:
            raise HTTPException(503, "Kein LLM konfiguriert (LLM_BASE_URL und LLM_API_KEY setzen)")
        treffer = _suche(request, conn, eingabe.frage, eingabe.k)
        antwort = antwortgeber.antworte(eingabe.frage, [t.absatz for t in treffer])
        return FrageAntwort(antwort=antwort, quellen=treffer)

    return app


def _suche(request: Request, conn, q: str, k: int) -> list[TrefferAntwort]:
    (vektor,) = request.app.state.embedder.embed_query([q])
    return [TrefferAntwort(**vars(t)) for t in db.suche(conn, vektor, k)]


def app_aus_umgebung() -> FastAPI:
    return erstelle_app(os.environ["DATABASE_URL"], antwortgeber=aus_umgebung())
