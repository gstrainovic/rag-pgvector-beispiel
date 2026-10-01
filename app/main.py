"""FastAPI-Dienst: Dokumente hochladen, semantisch suchen, Fragen streamen. Die Oberfläche liegt in web/ (Next.js).

Die Demo läuft öffentlich ohne Anmeldung. Darum: Beispieldokumente sind immer geladen, Besucher sehen
daneben nur die eigenen Uploads (anonymes Sitzungs-Cookie), Uploads verfallen, und app/grenzen.py
deckelt die Kosten beim Modellanbieter.
"""

import asyncio
import json
import logging
import os
import re
import secrets
from collections.abc import Callable, Iterator
from contextlib import asynccontextmanager, suppress
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, field_validator
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app import db
from app.anbieter import KONTINGENT_MELDUNG, AnbieterKontingent
from app.chunking import in_absaetze
from app.dateien import MAX_BYTES, DateiFehler, text_aus_datei
from app.embedding import Embedder
from app.embedding import aus_umgebung as embedder_aus_umgebung
from app.grenzen import Grenzen, MinutenFenster
from app.llm import Antwortgeber
from app.llm import aus_umgebung as llm_aus_umgebung

log = logging.getLogger("rag")
BEISPIELE_ORDNER = Path(__file__).resolve().parent / "beispiele"
BEISPIEL_MEDIENTYPEN = {".md": "text/markdown; charset=utf-8", ".pdf": "application/pdf"}

SITZUNG_COOKIE = "rag_sitzung"
SITZUNG_TAGE = 30
_SITZUNG_GUELTIG = re.compile(r"[A-Za-z0-9_-]{32,64}")
# Diese Pfade zeigen allen dasselbe und brauchen keine Sitzung
_OHNE_SITZUNG = ("/api/info", "/api/beispiele")

MAX_FRAGE_ZEICHEN = 500
MAX_K = 10
TAGESLIMIT_MELDUNG = "Tageslimit der Demo erreicht, morgen geht es weiter."


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
    beispiel: bool


class TrefferAntwort(BaseModel):
    titel: str
    absatz: str
    score: float


class SucheAntwort(BaseModel):
    treffer: list[TrefferAntwort]


class FrageEingabe(BaseModel):
    frage: str = Field(min_length=1, max_length=MAX_FRAGE_ZEICHEN)
    k: int = Field(default=5, ge=1, le=MAX_K)


class BeispielDatei(BaseModel):
    titel: str
    dateiname: str
    groesse: int


class InfoAntwort(BaseModel):
    llm_modell: str
    llm_basis_url: str
    embedder: str
    anzahl_dokumente: int
    # für einen Tagescheck von aussen; die Oberfläche zeigt sie nicht
    fragen_heute: int
    limit_fragen_pro_tag: int
    uploads_heute: int


class SitzungsMiddleware:
    """Gibt jedem Besucher eine zufällige, anonyme Sitzung (Cookie) und legt sie in request.state.sitzung ab.

    Reine ASGI-Middleware, damit auch gestreamte Antworten (SSE) das Cookie tragen und nichts gepuffert wird.
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        pfad = scope.get("path", "")
        if scope["type"] != "http" or not pfad.startswith("/api/") or pfad.startswith(_OHNE_SITZUNG):
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        zustand = scope.setdefault("state", {})
        vorhanden = request.cookies.get(SITZUNG_COOKIE, "")
        if _SITZUNG_GUELTIG.fullmatch(vorhanden):
            zustand["sitzung"] = vorhanden
            await self.app(scope, receive, send)
            return

        neu = secrets.token_urlsafe(32)
        zustand["sitzung"] = neu
        cookie = f"{SITZUNG_COOKIE}={neu}; HttpOnly; Max-Age={SITZUNG_TAGE * 24 * 3600}; Path=/; SameSite=Lax"
        if request.headers.get("x-forwarded-proto", "").split(",")[0].strip() == "https":
            cookie += "; Secure"

        async def send_mit_cookie(message: Message) -> None:
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message).append("set-cookie", cookie)
            await send(message)

        await self.app(scope, receive, send_mit_cookie)


def _jetzt() -> datetime:
    return datetime.now(UTC)


def erstelle_app(
    datenbank_url: str,
    embedder: Embedder | None = None,
    antwortgeber: Antwortgeber | None = None,
    grenzen: Grenzen | None = None,
    uhr: Callable[[], datetime] = _jetzt,
    beispiele_laden: bool = True,
) -> FastAPI:
    grenzen = grenzen or Grenzen()
    minutenfenster = MinutenFenster(grenzen.fragen_pro_minute_ip)

    def raeume_auf(conn) -> None:
        geloescht = db.loesche_abgelaufene(conn, vor=uhr() - timedelta(hours=grenzen.lebensdauer_stunden))
        if geloescht:
            log.info("%s abgelaufene Uploads gelöscht", geloescht)

    def wartung(app: FastAPI) -> None:
        """Abgelaufene Uploads löschen und die Beispiele sicherstellen. Fehler beim Embedder sind kein Abbruchgrund."""
        minutenfenster.saeubere(uhr())  # IP-Adressen nicht länger im Speicher halten als nötig
        with db.verbinde(datenbank_url) as conn:
            raeume_auf(conn)
            conn.commit()
            if beispiele_laden and not app.state.beispiele_bereit:
                try:
                    _stelle_beispiele_sicher(conn, app.state.embedder)
                    app.state.beispiele_bereit = True
                except Exception as e:  # noqa: BLE001 – z. B. Ollama lädt die Modelle noch
                    conn.rollback()
                    log.warning("Beispieldokumente noch nicht geladen (%s), neuer Versuch folgt", e)

    async def wartung_im_hintergrund(app: FastAPI) -> None:
        while True:
            await asyncio.sleep(60 if app.state.beispiele_bereit or not beispiele_laden else 10)
            try:
                await asyncio.to_thread(wartung, app)
            except Exception:
                log.exception("Wartung fehlgeschlagen")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.embedder = embedder or embedder_aus_umgebung()
        app.state.antwortgeber = antwortgeber or llm_aus_umgebung()
        app.state.beispiele_bereit = False
        db.migriere(datenbank_url, dimension=app.state.embedder.dimension)
        log.info("LLM %s @ %s, Embedder %s", app.state.antwortgeber.modell,
                 app.state.antwortgeber.basis_url, app.state.embedder.name)
        wartung(app)
        aufgabe = asyncio.create_task(wartung_im_hintergrund(app))
        yield
        aufgabe.cancel()
        with suppress(asyncio.CancelledError):
            await aufgabe

    app = FastAPI(title="RAG mit pgvector – Demo", lifespan=lifespan)
    app.add_middleware(SitzungsMiddleware)
    api = APIRouter(prefix="/api")

    @app.exception_handler(AnbieterKontingent)
    def kontingent_erreicht(request: Request, fehler: AnbieterKontingent) -> JSONResponse:
        # Besucher sehen eine freundliche Meldung; die Antwort des Anbieters bleibt im Protokoll
        log.warning("Kontingent beim Modell-Anbieter erreicht: %s", fehler)
        return JSONResponse({"detail": KONTINGENT_MELDUNG}, status_code=429)

    def verbindung():
        with db.verbinde(datenbank_url) as conn:
            yield conn

    def sitzung(request: Request) -> str:
        return request.state.sitzung

    Conn = Annotated[db.psycopg.Connection, Depends(verbindung)]
    Sitzung = Annotated[str, Depends(sitzung)]

    def frage_erlaubt(request: Request, conn: Conn) -> None:
        """Erst die Grenze je Minute und IP (kostet nichts), dann das globale Tageslimit."""
        warten = minutenfenster.erlaube(_client_ip(request), uhr())
        if warten:
            log.warning("Minutenlimit einer Adresse erreicht")  # die Adresse selbst kommt in kein Protokoll
            raise HTTPException(
                429,
                f"Zu viele Fragen in kurzer Zeit (höchstens {grenzen.fragen_pro_minute_ip} pro Minute). "
                f"Bitte in {warten} Sekunden noch einmal versuchen.",
                headers={"Retry-After": str(warten)},
            )
        if not db.erhoehe_zaehler(conn, uhr().date(), "fragen", grenzen.fragen_pro_tag):
            log.warning("Tageslimit Fragen (%s) erreicht", grenzen.fragen_pro_tag)
            raise HTTPException(429, TAGESLIMIT_MELDUNG)
        conn.commit()  # gezählt ist gezählt, auch wenn danach etwas scheitert

    FrageErlaubt = Depends(frage_erlaubt)

    def nimm_auf(request: Request, conn, sitzung_id: str, texte: list[tuple[str, str]]) -> list[DokumentAntwort]:
        """Prüft alle Grenzen, bevor ein einziges Embedding gerechnet wird, und speichert dann alles zusammen."""
        zerlegt: list[tuple[str, list[str]]] = []
        for titel, text in texte:
            absaetze = in_absaetze(text)
            if not absaetze:
                raise HTTPException(422, f"«{titel}» enthält keinen lesbaren Text")
            if len(absaetze) > grenzen.absaetze_pro_dokument:
                raise HTTPException(
                    413,
                    f"«{titel}» hat {len(absaetze)} Absätze, die Demo nimmt höchstens "
                    f"{grenzen.absaetze_pro_dokument} Absätze pro Dokument.",
                )
            zerlegt.append((titel, absaetze))

        raeume_auf(conn)
        if db.anzahl_dokumente(conn, sitzung=sitzung_id) + len(zerlegt) > grenzen.dokumente_pro_sitzung:
            raise HTTPException(
                429,
                f"Die Demo hält höchstens {grenzen.dokumente_pro_sitzung} eigene Dokumente pro Besucher. "
                "Löschen Sie ältere eigene Dokumente, um Platz zu schaffen.",
            )
        conn.commit()
        if not db.erhoehe_zaehler(conn, uhr().date(), "uploads", grenzen.uploads_pro_tag, um=len(zerlegt)):
            log.warning("Tageslimit Uploads (%s) erreicht", grenzen.uploads_pro_tag)
            raise HTTPException(429, TAGESLIMIT_MELDUNG)
        conn.commit()

        embedder_: Embedder = request.app.state.embedder
        with conn.transaction():
            return [
                DokumentAntwort(
                    id=db.speichere_dokument(conn, titel, absaetze, embedder_.embed(absaetze), sitzung=sitzung_id),
                    titel=titel,
                    anzahl_absaetze=len(absaetze),
                )
                for titel, absaetze in zerlegt
            ]

    def suche(request: Request, conn, sitzung_id: str, q: str, k: int) -> list[TrefferAntwort]:
        (vektor,) = request.app.state.embedder.embed_query([q])
        return [TrefferAntwort(**vars(t)) for t in db.suche(conn, vektor, k, sitzung=sitzung_id)]

    @api.post("/dokumente", response_model=DokumentAntwort, status_code=201)
    def dokument_aufnehmen(eingabe: DokumentEingabe, request: Request, conn: Conn, sitzung_id: Sitzung):
        return nimm_auf(request, conn, sitzung_id, [(eingabe.titel, eingabe.text)])[0]

    @api.post("/dokumente/upload", response_model=list[DokumentAntwort], status_code=201)
    async def dokumente_hochladen(dateien: list[UploadFile], request: Request, conn: Conn, sitzung_id: Sitzung):
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
        return nimm_auf(request, conn, sitzung_id, texte)

    @api.get("/dokumente", response_model=list[DokumentEintrag])
    def dokumente_auflisten(conn: Conn, sitzung_id: Sitzung):
        raeume_auf(conn)
        return [DokumentEintrag(**vars(d)) for d in db.liste_dokumente(conn, sitzung=sitzung_id)]

    @api.delete("/dokumente/{dok_id}", status_code=204, response_class=Response)
    def dokument_loeschen(dok_id: int, conn: Conn, sitzung_id: Sitzung):
        if db.ist_beispiel(conn, dok_id):
            raise HTTPException(403, "Beispieldokumente lassen sich nicht löschen")
        # fremde Dokumente gibt es für diesen Besucher nicht: gleiche Antwort wie bei einer unbekannten ID
        if not db.loesche_dokument(conn, dok_id, sitzung=sitzung_id):
            raise HTTPException(404, "Dokument nicht gefunden")

    @api.get("/beispiele", response_model=list[BeispielDatei])
    def beispiele_auflisten():
        return [
            BeispielDatei(titel=p.stem, dateiname=p.name, groesse=p.stat().st_size)
            for p in _beispiel_dateien().values()
        ]

    @api.get("/beispiele/{dateiname}", response_class=FileResponse)
    def beispiel_herunterladen(dateiname: str):
        # Kein Pfad aus der Anfrage: der Name muss einer Datei im Ordner genau entsprechen
        pfad = _beispiel_dateien().get(dateiname)
        if pfad is None:
            raise HTTPException(404, "Beispieldatei nicht gefunden")
        return FileResponse(
            pfad,
            filename=pfad.name,
            media_type=BEISPIEL_MEDIENTYPEN[pfad.suffix],
            content_disposition_type="attachment",
        )

    @api.get("/suche", response_model=SucheAntwort, dependencies=[FrageErlaubt])
    def suchen(
        request: Request,
        conn: Conn,
        sitzung_id: Sitzung,
        q: Annotated[str, Query(min_length=1, max_length=MAX_FRAGE_ZEICHEN)],
        k: Annotated[int, Query(ge=1, le=MAX_K)] = 5,
    ):
        return SucheAntwort(treffer=suche(request, conn, sitzung_id, q, k))

    @api.post("/frage", dependencies=[FrageErlaubt])
    def fragen(eingabe: FrageEingabe, request: Request, conn: Conn, sitzung_id: Sitzung):
        antwortgeber_: Antwortgeber = request.app.state.antwortgeber
        treffer = suche(request, conn, sitzung_id, eingabe.frage, eingabe.k)

        def events() -> Iterator[str]:
            yield _sse("quellen", [t.model_dump() for t in treffer])
            if not treffer:
                yield _sse("token", {"text": "Es sind keine Dokumente geladen. Bitte zuerst ein Dokument hochladen."})
            else:
                try:
                    for text in antwortgeber_.antworte_stream(eingabe.frage, [t.absatz for t in treffer]):
                        yield _sse("token", {"text": text})
                except AnbieterKontingent as e:
                    log.warning("Kontingent beim Modell-Anbieter erreicht: %s", e)
                    yield _sse("fehler", {"meldung": KONTINGENT_MELDUNG, "art": "grenze"})
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
        heute = uhr().date()
        return InfoAntwort(
            llm_modell=request.app.state.antwortgeber.modell,
            llm_basis_url=request.app.state.antwortgeber.basis_url,
            embedder=request.app.state.embedder.name,
            anzahl_dokumente=db.anzahl_dokumente(conn),
            fragen_heute=db.zaehlerstand(conn, heute, "fragen"),
            limit_fragen_pro_tag=grenzen.fragen_pro_tag,
            uploads_heute=db.zaehlerstand(conn, heute, "uploads"),
        )

    app.include_router(api)
    return app


def _stelle_beispiele_sicher(conn, embedder: Embedder) -> None:
    """Die Texte aus app/beispiele/ sind genau die Dokumente ohne Sitzung: Fehlendes anlegen, Überzähliges entfernen."""
    dateien = sorted(BEISPIELE_ORDNER.glob("*.md"))
    entfernt = db.loesche_beispiele_ausser(conn, [p.stem for p in dateien])
    if entfernt:
        log.info("%s Dokumente ohne Sitzung entfernt, die kein Beispiel sind", entfernt)
    vorhanden = db.beispiel_titel(conn)
    for pfad in dateien:
        if pfad.stem not in vorhanden:
            absaetze = in_absaetze(pfad.read_text(encoding="utf-8"))
            db.speichere_dokument(conn, pfad.stem, absaetze, embedder.embed(absaetze))
            log.info("Beispieldokument «%s» geladen (%s Absätze)", pfad.stem, len(absaetze))
    conn.commit()


def _beispiel_dateien() -> dict[str, Path]:
    """Dateiname → Pfad für alle herunterladbaren Dateien direkt in app/beispiele/ (.md und .pdf)."""
    return {
        p.name: p
        for p in sorted(BEISPIELE_ORDNER.iterdir())
        if p.is_file() and p.suffix in BEISPIEL_MEDIENTYPEN and not p.name.startswith(".")
    }


def _client_ip(request: Request) -> str:
    """Adresse des Besuchers. Der letzte Eintrag in X-Forwarded-For stammt vom eigenen Proxy (Caddy bzw. Next),
    frühere Einträge kann der Aufrufer frei erfinden."""
    kette = request.headers.get("x-forwarded-for", "")
    letzter = kette.split(",")[-1].strip()
    if letzter:
        return letzter
    return request.client.host if request.client else "unbekannt"


def _sse(event: str, daten: object) -> str:
    return f"event: {event}\ndata: {json.dumps(daten, ensure_ascii=False)}\n\n"


def app_aus_umgebung() -> FastAPI:
    logging.basicConfig(level=logging.INFO)
    return erstelle_app(os.environ["DATABASE_URL"], grenzen=Grenzen.aus_umgebung())
