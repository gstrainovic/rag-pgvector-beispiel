import json
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import erstelle_app
from tests.test_pdf import erzeuge_pdf


class AntwortgeberAttrappe:
    modell = "attrappe-modell"
    basis_url = "http://attrappe/v1"

    def __init__(self, fehler: Exception | None = None):
        self.aufrufe = []
        self.fehler = fehler

    def antworte_stream(self, frage: str, kontexte: list[str]) -> Iterator[str]:
        self.aufrufe.append((frage, kontexte))
        if self.fehler:
            raise self.fehler
        yield "Attrappe: "
        yield f"{len(kontexte)} Kontexte"


@pytest.fixture
def attrappe():
    return AntwortgeberAttrappe()


@pytest.fixture
def client(datenbank_url, embedder, attrappe, conn):
    # ohne die Beispieldokumente; die prüft tests/test_demo_betrieb.py
    app = erstelle_app(datenbank_url, embedder=embedder, antwortgeber=attrappe, beispiele_laden=False)
    with TestClient(app) as c:
        yield c


TEXT = """Der Hund bellt im Garten.

Die Steuererklärung ist bis Ende März fällig.

Die Katze schläft auf dem Sofa."""


def sse_events(text: str) -> list[tuple[str, object]]:
    events = []
    for block in text.strip().split("\n\n"):
        event, daten = "message", ""
        for zeile in block.splitlines():
            if zeile.startswith("event:"):
                event = zeile[6:].strip()
            elif zeile.startswith("data:"):
                daten += zeile[5:].strip()
        events.append((event, json.loads(daten)))
    return events


# --- Dokumente per JSON (bestehend) ---------------------------------------------------------


def test_dokument_aufnehmen(client):
    r = client.post("/api/dokumente", json={"titel": "Alltag", "text": TEXT})
    assert r.status_code == 201
    body = r.json()
    assert body["titel"] == "Alltag"
    assert body["anzahl_absaetze"] == 3
    assert isinstance(body["id"], int)


def test_leerer_text_wird_abgelehnt(client):
    r = client.post("/api/dokumente", json={"titel": "Leer", "text": "   \n\n  "})
    assert r.status_code == 422


# --- Upload ---------------------------------------------------------------------------------


def test_upload_txt_und_md(client):
    r = client.post(
        "/api/dokumente/upload",
        files=[
            ("dateien", ("notiz.txt", TEXT.encode(), "text/plain")),
            ("dateien", ("faq.md", b"# FAQ\n\nErste Antwort.\n\nZweite Antwort.", "text/markdown")),
        ],
    )
    assert r.status_code == 201
    body = r.json()
    assert [d["titel"] for d in body] == ["notiz.txt", "faq.md"]
    assert body[0]["anzahl_absaetze"] == 3
    assert body[1]["anzahl_absaetze"] == 3
    assert all(isinstance(d["id"], int) for d in body)


def test_upload_pdf(client):
    pdf = erzeuge_pdf(["Die Heizung wird jährlich im Oktober gewartet.", "Der Filter wird alle drei Monate getauscht."])
    r = client.post("/api/dokumente/upload", files=[("dateien", ("wartung.pdf", pdf, "application/pdf"))])
    assert r.status_code == 201
    (dok,) = r.json()
    assert dok["titel"] == "wartung.pdf"
    assert dok["anzahl_absaetze"] == 2
    s = client.get("/api/suche", params={"q": "Wann wird die Heizung gewartet?", "k": 1}).json()
    assert "Oktober" in s["treffer"][0]["absatz"]


def test_upload_falsche_endung_ist_415(client):
    r = client.post("/api/dokumente/upload", files=[("dateien", ("bild.png", b"\x89PNG", "image/png"))])
    assert r.status_code == 415
    assert "pdf, txt, md" in r.json()["detail"]


def test_upload_zu_gross_ist_413(client):
    gross = b"a" * (20 * 1024 * 1024 + 1)
    r = client.post("/api/dokumente/upload", files=[("dateien", ("gross.txt", gross, "text/plain"))])
    assert r.status_code == 413
    assert "20 MB" in r.json()["detail"]


def test_upload_ohne_text_ist_422(client):
    pdf = erzeuge_pdf([""])
    r = client.post("/api/dokumente/upload", files=[("dateien", ("leer.pdf", pdf, "application/pdf"))])
    assert r.status_code == 422
    assert "leer.pdf" in r.json()["detail"]


def test_upload_ist_atomar_bei_fehler_in_zweiter_datei(client):
    r = client.post(
        "/api/dokumente/upload",
        files=[
            ("dateien", ("gut.txt", b"Text.", "text/plain")),
            ("dateien", ("schlecht.exe", b"x", "application/octet-stream")),
        ],
    )
    assert r.status_code == 415
    assert client.get("/api/dokumente").json() == []


# --- Liste und Löschen -----------------------------------------------------------------------


def test_liste_und_loeschen(client):
    a = client.post("/api/dokumente", json={"titel": "A", "text": "Eins.\n\nZwei."}).json()["id"]
    b = client.post("/api/dokumente", json={"titel": "B", "text": "Drei."}).json()["id"]
    liste = client.get("/api/dokumente").json()
    assert [(d["id"], d["titel"], d["anzahl_absaetze"]) for d in liste] == [(a, "A", 2), (b, "B", 1)]
    assert all("erstellt" in d for d in liste)

    assert client.delete(f"/api/dokumente/{a}").status_code == 204
    assert [d["id"] for d in client.get("/api/dokumente").json()] == [b]
    assert client.delete(f"/api/dokumente/{a}").status_code == 404


# --- Suche -----------------------------------------------------------------------------------


def test_suche_liefert_treffer_mit_score(client):
    client.post("/api/dokumente", json={"titel": "Alltag", "text": TEXT})
    r = client.get("/api/suche", params={"q": "Welches Tier macht Lärm?", "k": 2})
    assert r.status_code == 200
    treffer = r.json()["treffer"]
    assert len(treffer) == 2
    assert treffer[0]["titel"] == "Alltag"
    assert treffer[0]["absatz"] == "Der Hund bellt im Garten."
    assert treffer[0]["score"] >= treffer[1]["score"]


def test_suche_ohne_q_ist_422(client):
    assert client.get("/api/suche").status_code == 422


# --- Frage als SSE ---------------------------------------------------------------------------


def test_frage_streamt_quellen_tokens_und_ende(client, attrappe):
    client.post("/api/dokumente", json={"titel": "Alltag", "text": TEXT})
    r = client.post("/api/frage", json={"frage": "Welches Tier bellt?", "k": 2})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    events = sse_events(r.text)
    assert events[0][0] == "quellen"
    quellen = events[0][1]
    assert len(quellen) == 2
    assert quellen[0]["titel"] == "Alltag"
    assert quellen[0]["absatz"] == "Der Hund bellt im Garten."
    assert isinstance(quellen[0]["score"], float)
    tokens = [d["text"] for e, d in events if e == "token"]
    assert tokens == ["Attrappe: ", "2 Kontexte"]
    assert events[-1] == ("ende", {})
    frage, kontexte = attrappe.aufrufe[0]
    assert frage == "Welches Tier bellt?"
    assert kontexte[0] == "Der Hund bellt im Garten."


def test_frage_ohne_dokumente_fragt_kein_llm(client, attrappe):
    r = client.post("/api/frage", json={"frage": "Egal?"})
    events = sse_events(r.text)
    assert events[0] == ("quellen", [])
    tokens = "".join(d["text"] for e, d in events if e == "token")
    assert "keine Dokumente" in tokens
    assert attrappe.aufrufe == []
    assert events[-1] == ("ende", {})


def test_frage_meldet_llm_fehler_als_event(datenbank_url, embedder, conn):
    attrappe = AntwortgeberAttrappe(fehler=ConnectionError("Ollama nicht erreichbar"))
    app = erstelle_app(datenbank_url, embedder=embedder, antwortgeber=attrappe, beispiele_laden=False)
    with TestClient(app) as c:
        c.post("/api/dokumente", json={"titel": "A", "text": "Eins."})
        r = c.post("/api/frage", json={"frage": "Was?"})
    events = sse_events(r.text)
    fehler = [d for e, d in events if e == "fehler"]
    assert len(fehler) == 1
    assert "Ollama nicht erreichbar" in fehler[0]["meldung"]
    assert events[-1] == ("ende", {})


# --- Info und Beispiele ----------------------------------------------------------------------


def test_info(client):
    client.post("/api/dokumente", json={"titel": "A", "text": "Eins."})
    info = client.get("/api/info").json()
    assert info["llm_modell"] == "attrappe-modell"
    assert info["llm_basis_url"] == "http://attrappe/v1"
    assert info["embedder"].startswith("fastembed:")
    assert info["anzahl_dokumente"] == 1
    assert (info["fragen_heute"], info["limit_fragen_pro_tag"], info["uploads_heute"]) == (0, 300, 1)


# --- Beispieldokumente herunterladen ---------------------------------------------------------

BEISPIEL_TITEL = ["FAQ Schreinerei Holzwerk", "Hausordnung Sonnenhof", "Wartungsanleitung Heizung HZ-40"]


def test_beispiele_liste_nennt_titel_dateiname_und_groesse(client):
    r = client.get("/api/beispiele")
    assert r.status_code == 200
    liste = r.json()
    assert [(e["titel"], e["dateiname"]) for e in liste] == [
        (t, f"{t}.{endung}") for t in BEISPIEL_TITEL for endung in ("md", "pdf")
    ]
    assert all(isinstance(e["groesse"], int) and e["groesse"] > 500 for e in liste)


def test_beispiel_download_als_anhang(client):
    r = client.get("/api/beispiele/Hausordnung Sonnenhof.pdf")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.headers["content-disposition"].startswith("attachment;")
    assert "Hausordnung" in r.headers["content-disposition"]
    assert r.content.startswith(b"%PDF-")
    groesse = next(e["groesse"] for e in client.get("/api/beispiele").json() if e["dateiname"].endswith("Sonnenhof.pdf"))
    assert len(r.content) == groesse

    md = client.get("/api/beispiele/Hausordnung Sonnenhof.md")
    assert md.status_code == 200
    assert md.headers["content-type"].startswith("text/markdown")
    assert md.headers["content-disposition"].startswith("attachment;")
    assert "Nachtruhe" in md.text


@pytest.mark.parametrize(
    "pfad",
    [
        "/api/beispiele/gibtsnicht.pdf",
        "/api/beispiele/..",
        "/api/beispiele/../main.py",
        "/api/beispiele/..%2Fmain.py",
        "/api/beispiele/%2E%2E%2Fmain.py",
        "/api/beispiele/..%5Cmain.py",
        "/api/beispiele/%2Fetc%2Fpasswd",
        "/api/beispiele/.versteckt.md",
    ],
)
def test_beispiel_download_ohne_pfad_traversal(client, pfad):
    r = client.get(pfad)
    assert r.status_code == 404
    assert b"import" not in r.content and b"root:" not in r.content


def test_beispiel_download_nur_md_und_pdf(client, monkeypatch, tmp_path):
    (tmp_path / "geheim.txt").write_text("nicht ausliefern")
    (tmp_path / "Notiz.md").write_text("# Notiz\n\nText.")
    monkeypatch.setattr("app.main.BEISPIELE_ORDNER", tmp_path)
    assert client.get("/api/beispiele/geheim.txt").status_code == 404
    assert client.get("/api/beispiele/Notiz.md").status_code == 200
    assert [e["dateiname"] for e in client.get("/api/beispiele").json()] == ["Notiz.md"]


def test_beispiel_pdf_laesst_sich_hochladen_und_durchsuchen(client):
    pdf = client.get("/api/beispiele/Hausordnung Sonnenhof.pdf").content
    r = client.post("/api/dokumente/upload", files=[("dateien", ("Hausordnung Sonnenhof.pdf", pdf, "application/pdf"))])
    assert r.status_code == 201
    assert r.json()[0]["anzahl_absaetze"] >= 3
    s = client.get("/api/suche", params={"q": "Wann ist Nachtruhe?", "k": 1}).json()
    assert "22 Uhr" in s["treffer"][0]["absatz"]


# --- Keine Oberfläche mehr in der API --------------------------------------------------------


def test_api_liefert_keine_oberflaeche(client):
    assert client.get("/").status_code == 404
    assert client.get("/irgendeine/route").status_code == 404
    assert client.get("/docs").status_code == 200
