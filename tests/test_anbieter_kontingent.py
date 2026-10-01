"""Der Modell-Anbieter lehnt ab, weil Kontingent oder Ratenlimit des Kontos erreicht sind (Ausgabenlimit 0)."""

import httpx
import pytest
from fastapi.testclient import TestClient

from app.anbieter import KONTINGENT_MELDUNG, AnbieterKontingent
from app.embedding import OpenAiKompatiblerEmbedder
from app.llm import OpenAiKompatiblerAntwortgeber
from app.main import erstelle_app
from tests.test_api import AntwortgeberAttrappe, sse_events

ROH = "Requests rate limit exceeded for org 1234-geheim"


def client_mit_status(status: int) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(status, json={"message": ROH})))


@pytest.mark.parametrize("status", [402, 403, 429])
def test_llm_meldet_erschoepftes_kontingent_als_eigene_ausnahme(status):
    adapter = OpenAiKompatiblerAntwortgeber("https://llm.example/v1", "k", "m", client=client_mit_status(status))
    with pytest.raises(AnbieterKontingent):
        list(adapter.antworte_stream("Frage?", ["Kontext"]))


def test_llm_andere_fehler_bleiben_runtime_error():
    adapter = OpenAiKompatiblerAntwortgeber("https://llm.example/v1", "k", "m", client=client_mit_status(500))
    with pytest.raises(RuntimeError, match="500") as info:
        list(adapter.antworte_stream("Frage?", ["Kontext"]))
    assert not isinstance(info.value, AnbieterKontingent)


@pytest.mark.parametrize("status", [402, 403, 429])
def test_embedder_meldet_erschoepftes_kontingent_als_eigene_ausnahme(status):
    emb = OpenAiKompatiblerEmbedder("https://llm.example/v1", "k", "m", client=client_mit_status(status))
    with pytest.raises(AnbieterKontingent):
        emb.embed(["x"])


def test_embedder_schickt_absaetze_gebuendelt():
    anfragen = []

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        texte = json.loads(request.content)["input"]
        anfragen.append(len(texte))
        return httpx.Response(200, json={"data": [{"index": i, "embedding": [1.0, 0.0]} for i in range(len(texte))]})

    emb = OpenAiKompatiblerEmbedder(
        "https://llm.example/v1", "k", "m", client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    assert len(emb.embed([f"Absatz {i}" for i in range(200)])) == 200
    assert anfragen == [32, 32, 32, 32, 32, 32, 8]  # 7 Anfragen statt 200


class KontingentEmbedder:
    def __init__(self, embedder, erschoepft=True):
        self.name, self.dimension, self._embedder, self.erschoepft = embedder.name, embedder.dimension, embedder, erschoepft

    def embed(self, texte):
        if self.erschoepft:
            raise AnbieterKontingent(f"Embedding-Dienst antwortet mit 429: {ROH}")
        return self._embedder.embed(texte)

    def embed_query(self, texte):
        if self.erschoepft:
            raise AnbieterKontingent(f"Embedding-Dienst antwortet mit 429: {ROH}")
        return self._embedder.embed_query(texte)


def test_frage_zeigt_freundliche_meldung_statt_des_rohen_fehlers(datenbank_url, embedder, conn):
    attrappe = AntwortgeberAttrappe(fehler=AnbieterKontingent(f"LLM antwortet mit 429: {ROH}"))
    app = erstelle_app(datenbank_url, embedder=embedder, antwortgeber=attrappe, beispiele_laden=False)
    with TestClient(app) as c:
        c.post("/api/dokumente", json={"titel": "A", "text": "Eins."})
        r = c.post("/api/frage", json={"frage": "Was?"})
    (fehler,) = [d for e, d in sse_events(r.text) if e == "fehler"]
    assert fehler == {"meldung": KONTINGENT_MELDUNG, "art": "grenze"}
    assert "Monatskontingent beim Modell-Anbieter" in KONTINGENT_MELDUNG
    assert ROH not in r.text


def test_upload_und_frage_antworten_mit_429_wenn_der_embedder_ablehnt(datenbank_url, embedder, conn):
    kontingent = KontingentEmbedder(embedder)
    app = erstelle_app(datenbank_url, embedder=kontingent, antwortgeber=AntwortgeberAttrappe(), beispiele_laden=False)
    with TestClient(app) as c:
        upload = c.post("/api/dokumente/upload", files=[("dateien", ("a.txt", b"Text.", "text/plain"))])
        frage = c.post("/api/frage", json={"frage": "Was?"})
        assert c.get("/api/dokumente").json() == []
    for r in (upload, frage):
        assert r.status_code == 429
        assert r.json() == {"detail": KONTINGENT_MELDUNG}
        assert ROH not in r.text
