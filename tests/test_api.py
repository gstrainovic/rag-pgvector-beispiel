import pytest
from fastapi.testclient import TestClient

from app.main import erstelle_app


class AntwortgeberAttrappe:
    def __init__(self):
        self.aufrufe = []

    def antworte(self, frage: str, kontexte: list[str]) -> str:
        self.aufrufe.append((frage, kontexte))
        return f"Attrappe: {len(kontexte)} Kontexte"


@pytest.fixture
def attrappe():
    return AntwortgeberAttrappe()


@pytest.fixture
def client(datenbank_url, embedder, attrappe, conn):
    app = erstelle_app(datenbank_url, embedder=embedder, antwortgeber=attrappe)
    with TestClient(app) as c:
        yield c


TEXT = """Der Hund bellt im Garten.

Die Steuererklärung ist bis Ende März fällig.

Die Katze schläft auf dem Sofa."""


def test_dokument_aufnehmen(client):
    r = client.post("/dokumente", json={"titel": "Alltag", "text": TEXT})
    assert r.status_code == 201
    body = r.json()
    assert body["titel"] == "Alltag"
    assert body["anzahl_absaetze"] == 3
    assert isinstance(body["id"], int)


def test_leerer_text_wird_abgelehnt(client):
    r = client.post("/dokumente", json={"titel": "Leer", "text": "   \n\n  "})
    assert r.status_code == 422


def test_suche_liefert_treffer_mit_score(client):
    client.post("/dokumente", json={"titel": "Alltag", "text": TEXT})
    r = client.get("/suche", params={"q": "Welches Tier macht Lärm?", "k": 2})
    assert r.status_code == 200
    treffer = r.json()["treffer"]
    assert len(treffer) == 2
    assert treffer[0] == {
        "titel": "Alltag",
        "absatz": "Der Hund bellt im Garten.",
        "score": pytest.approx(treffer[0]["score"]),
    }
    assert treffer[0]["score"] >= treffer[1]["score"]


def test_suche_k_standard_ist_5(client):
    client.post("/dokumente", json={"titel": "Zehn", "text": "\n\n".join(f"Absatz {i}." for i in range(10))})
    r = client.get("/suche", params={"q": "Absatz"})
    assert len(r.json()["treffer"]) == 5


def test_suche_ohne_q_ist_422(client):
    assert client.get("/suche").status_code == 422


def test_frage_gibt_treffer_als_kontext_an_llm(client, attrappe):
    client.post("/dokumente", json={"titel": "Alltag", "text": TEXT})
    r = client.post("/frage", json={"frage": "Welches Tier bellt?", "k": 2})
    assert r.status_code == 200
    body = r.json()
    assert body["antwort"] == "Attrappe: 2 Kontexte"
    assert len(body["quellen"]) == 2
    assert body["quellen"][0]["absatz"] == "Der Hund bellt im Garten."
    frage, kontexte = attrappe.aufrufe[0]
    assert frage == "Welches Tier bellt?"
    assert kontexte[0] == "Der Hund bellt im Garten."


def test_frage_ohne_llm_ist_503(datenbank_url, embedder, conn):
    app = erstelle_app(datenbank_url, embedder=embedder, antwortgeber=None)
    with TestClient(app) as c:
        r = c.post("/frage", json={"frage": "Egal?"})
    assert r.status_code == 503
    assert "LLM" in r.json()["detail"]
