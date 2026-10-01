"""Öffentliche Demo: Beispiele als Standard, Besucher getrennt per Sitzungs-Cookie, Grenzen gegen Kosten."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app import db
from app.grenzen import Grenzen
from app.main import SITZUNG_COOKIE, erstelle_app
from tests.test_api import AntwortgeberAttrappe, sse_events

BEISPIEL_TITEL = ["FAQ Schreinerei Holzwerk", "Hausordnung Sonnenhof", "Wartungsanleitung Heizung HZ-40"]


class Uhr:
    """Stellbare Uhr, damit kein Test auf die echte Zeit wartet."""

    def __init__(self):
        self.jetzt = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.jetzt

    def vor(self, **delta) -> None:
        self.jetzt += timedelta(**delta)


@pytest.fixture
def uhr():
    return Uhr()


@pytest.fixture
def baue(datenbank_url, embedder, conn, uhr):
    """Erzeugt die App mit Attrappe; liefert einen Besucher (TestClient mit eigenem Cookie-Speicher)."""
    offen = []

    def _baue(beispiele_laden=False, antwortgeber=None, embedder_=None, **grenzen):
        app = erstelle_app(
            datenbank_url,
            embedder=embedder_ or embedder,
            antwortgeber=antwortgeber or AntwortgeberAttrappe(),
            grenzen=Grenzen(**grenzen),
            uhr=uhr,
            beispiele_laden=beispiele_laden,
        )
        client = TestClient(app)
        client.__enter__()
        offen.append(client)
        return client

    yield _baue
    for client in offen:
        client.__exit__(None, None, None)


def besucher(client: TestClient) -> TestClient:
    """Zweiter Browser an derselben App (teilt Datenbank, Zähler und Minutenfenster)."""
    return TestClient(client.app)


def lade_hoch(client, name="notiz.txt", text="Der Hund bellt im Garten.\n\nDie Katze schläft."):
    return client.post("/api/dokumente/upload", files=[("dateien", (name, text.encode(), "text/plain"))])


# --- Beispiele sind Standard -------------------------------------------------------------------


def test_start_laedt_die_beispiele_und_ein_zweiter_start_legt_nichts_doppelt_an(baue):
    erster = baue(beispiele_laden=True)
    liste = erster.get("/api/dokumente").json()
    assert [d["titel"] for d in liste] == BEISPIEL_TITEL
    assert all(d["beispiel"] is True and d["anzahl_absaetze"] >= 9 for d in liste)

    zweiter = baue(beispiele_laden=True)
    assert [d["id"] for d in zweiter.get("/api/dokumente").json()] == [d["id"] for d in liste]


def test_start_ergaenzt_ein_fehlendes_beispiel_und_entfernt_bestand_ohne_sitzung(baue, conn, embedder):
    baue(beispiele_laden=True)
    conn.execute("DELETE FROM dokumente WHERE titel = %s", (BEISPIEL_TITEL[0],))
    db.speichere_dokument(conn, "alter-upload.pdf", ["x"], embedder.embed(["x"]))
    conn.commit()
    titel = [d["titel"] for d in baue(beispiele_laden=True).get("/api/dokumente").json()]
    assert sorted(titel) == BEISPIEL_TITEL


def test_beispiele_stehen_oben_und_eigene_dokumente_darunter(baue):
    client = baue(beispiele_laden=True)
    assert lade_hoch(client).status_code == 201
    liste = client.get("/api/dokumente").json()
    assert [(d["titel"], d["beispiel"]) for d in liste] == [*[(t, True) for t in BEISPIEL_TITEL], ("notiz.txt", False)]


def test_beispiel_laesst_sich_nicht_loeschen(baue):
    client = baue(beispiele_laden=True)
    beispiel = client.get("/api/dokumente").json()[0]
    r = client.delete(f"/api/dokumente/{beispiel['id']}")
    assert r.status_code == 403
    assert "Beispiel" in r.json()["detail"]
    assert len(client.get("/api/dokumente").json()) == 3


def test_es_gibt_keinen_endpunkt_mehr_zum_laden_der_beispiele(baue):
    assert baue().post("/api/beispiele").status_code == 405


def test_start_gelingt_auch_wenn_der_embedder_noch_nicht_bereit_ist(baue, embedder):
    class NochNichtBereit:
        name = embedder.name
        dimension = embedder.dimension

        def embed(self, texte):
            raise ConnectionError("Ollama lädt noch")

        embed_query = embed

    client = baue(beispiele_laden=True, embedder_=NochNichtBereit())
    assert client.get("/api/dokumente").json() == []
    assert client.get("/api/info").status_code == 200


# --- Sitzung per Cookie ------------------------------------------------------------------------


def test_erster_aufruf_setzt_das_sitzungs_cookie(baue):
    client = baue()
    r = client.get("/api/dokumente")
    cookie = r.headers["set-cookie"]
    assert cookie.startswith(f"{SITZUNG_COOKIE}=")
    assert len(r.cookies[SITZUNG_COOKIE]) >= 32
    teile = {t.strip().lower() for t in cookie.split(";")}
    assert {"httponly", "samesite=lax", "path=/", f"max-age={30 * 24 * 3600}"} <= teile
    assert "secure" not in teile

    assert "set-cookie" not in client.get("/api/dokumente").headers
    assert besucher(client).get("/api/dokumente").cookies[SITZUNG_COOKIE] != r.cookies[SITZUNG_COOKIE]


def test_cookie_ist_secure_hinter_tls_und_ein_unbrauchbarer_wert_wird_ersetzt(baue):
    client = baue()
    r = client.get("/api/dokumente", headers={"X-Forwarded-Proto": "https"})
    assert "secure" in {t.strip().lower() for t in r.headers["set-cookie"].split(";")}

    fremd = besucher(client)
    fremd.cookies.set(SITZUNG_COOKIE, "kurz")
    assert SITZUNG_COOKIE in fremd.get("/api/dokumente").headers["set-cookie"]


def test_auch_die_gestreamte_antwort_setzt_das_cookie(baue):
    r = baue().post("/api/frage", json={"frage": "Egal?"})
    assert r.headers["set-cookie"].startswith(f"{SITZUNG_COOKIE}=")
    assert sse_events(r.text)[-1] == ("ende", {})


def test_besucher_sehen_durchsuchen_und_loeschen_nur_eigene_dokumente(baue):
    attrappe = AntwortgeberAttrappe()
    anna = baue(beispiele_laden=True, antwortgeber=attrappe)
    bert = besucher(anna)
    (dok,) = lade_hoch(anna, "tiere.txt", "Der Hund Bello bellt im Garten.").json()

    assert "tiere.txt" in [d["titel"] for d in anna.get("/api/dokumente").json()]
    assert [d["titel"] for d in bert.get("/api/dokumente").json()] == BEISPIEL_TITEL

    frage = {"q": "Wie heisst der Hund, der im Garten bellt?", "k": 3}
    assert anna.get("/api/suche", params=frage).json()["treffer"][0]["titel"] == "tiere.txt"
    assert all(t["titel"] in BEISPIEL_TITEL for t in bert.get("/api/suche", params=frage).json()["treffer"])

    quellen = sse_events(bert.post("/api/frage", json={"frage": frage["q"], "k": 3}).text)[0][1]
    assert all(q["titel"] in BEISPIEL_TITEL for q in quellen)
    assert all("Bello" not in k for _, kontexte in attrappe.aufrufe for k in kontexte)

    assert bert.delete(f"/api/dokumente/{dok['id']}").status_code == 404
    assert anna.delete(f"/api/dokumente/{dok['id']}").status_code == 204


# --- Uploads verfallen nach 24 Stunden ---------------------------------------------------------


def test_uploads_werden_nach_24_stunden_geloescht(baue, uhr, conn):
    client = baue(beispiele_laden=True)
    lade_hoch(client, "alt.txt")
    conn.execute("UPDATE dokumente SET erstellt_am = %s WHERE titel = 'alt.txt'", (uhr() - timedelta(hours=23),))
    conn.commit()
    lade_hoch(client, "neu.txt")
    assert [d["titel"] for d in client.get("/api/dokumente").json()] == [*BEISPIEL_TITEL, "alt.txt", "neu.txt"]

    uhr.vor(hours=2)  # alt.txt ist jetzt 25 Stunden alt; die Liste räumt auf
    assert [d["titel"] for d in client.get("/api/dokumente").json()] == [*BEISPIEL_TITEL, "neu.txt"]


def test_start_raeumt_abgelaufene_uploads_auf(baue, uhr, conn, embedder):
    db.speichere_dokument(conn, "alt.txt", ["x"], embedder.embed(["x"]), sitzung="anna")
    conn.execute("UPDATE dokumente SET erstellt_am = %s", (uhr() - timedelta(hours=25),))
    conn.commit()
    baue()
    assert conn.execute("SELECT count(*) FROM dokumente").fetchone()[0] == 0


# --- Grenzen -----------------------------------------------------------------------------------


def test_standardwerte_der_grenzen_und_werte_aus_der_umgebung(monkeypatch):
    g = Grenzen()
    assert (g.fragen_pro_tag, g.fragen_pro_minute_ip, g.dokumente_pro_sitzung) == (300, 10, 25)
    assert (g.absaetze_pro_dokument, g.uploads_pro_tag, g.lebensdauer_stunden) == (200, 300, 24)
    monkeypatch.setenv("LIMIT_FRAGEN_PRO_TAG", "7")
    monkeypatch.setenv("LIMIT_UPLOADS_PRO_TAG", "")
    aus_env = Grenzen.aus_umgebung()
    assert aus_env.fragen_pro_tag == 7
    assert aus_env.uploads_pro_tag == 300


def test_tageslimit_fragen_gilt_fuer_alle_und_endet_mit_dem_utc_tag(baue, uhr):
    attrappe = AntwortgeberAttrappe()
    anna = baue(antwortgeber=attrappe, fragen_pro_tag=2)
    bert = besucher(anna)
    lade_hoch(anna)
    assert anna.post("/api/frage", json={"frage": "Eins?"}).status_code == 200
    assert bert.post("/api/frage", json={"frage": "Zwei?"}).status_code == 200

    r = anna.post("/api/frage", json={"frage": "Drei?"})
    assert r.status_code == 429
    assert "Tageslimit der Demo erreicht" in r.json()["detail"]
    assert bert.get("/api/suche", params={"q": "Hund"}).status_code == 429
    assert len(attrappe.aufrufe) == 1  # bert sieht annas Datei nicht, darum fragt nur anna das Modell

    uhr.jetzt = datetime(2026, 10, 1, 23, 59, tzinfo=UTC)
    assert anna.post("/api/frage", json={"frage": "Noch heute?"}).status_code == 429
    uhr.jetzt = datetime(2026, 10, 2, 0, 1, tzinfo=UTC)
    assert anna.post("/api/frage", json={"frage": "Morgen?"}).status_code == 200


def test_minutenlimit_je_ip_aus_x_forwarded_for(baue, uhr):
    client = baue(fragen_pro_minute_ip=2)
    von = lambda ip: {"X-Forwarded-For": ip}  # noqa: E731
    assert client.post("/api/frage", json={"frage": "1?"}, headers=von("203.0.113.5")).status_code == 200
    assert client.post("/api/frage", json={"frage": "2?"}, headers=von("203.0.113.5")).status_code == 200
    r = client.post("/api/frage", json={"frage": "3?"}, headers=von("203.0.113.5"))
    assert r.status_code == 429
    assert "Minute" in r.json()["detail"]
    assert int(r.headers["retry-after"]) >= 1

    # andere Adresse ist nicht betroffen; massgebend ist der letzte Eintrag (den setzt der eigene Proxy)
    assert client.post("/api/frage", json={"frage": "4?"}, headers=von("198.51.100.7")).status_code == 200
    assert client.post("/api/frage", json={"frage": "5?"}, headers=von("198.51.100.9, 203.0.113.5")).status_code == 429

    uhr.vor(seconds=61)
    assert client.post("/api/frage", json={"frage": "6?"}, headers=von("203.0.113.5")).status_code == 200


def test_abgewiesene_fragen_zaehlen_nicht_zum_tageslimit(baue):
    client = baue(fragen_pro_minute_ip=1)
    client.post("/api/frage", json={"frage": "1?"})
    assert client.post("/api/frage", json={"frage": "2?"}).status_code == 429
    assert client.get("/api/info").json()["fragen_heute"] == 1


def test_grenze_fuer_dokumente_je_sitzung_und_loeschen_schafft_platz(baue):
    anna = baue(dokumente_pro_sitzung=2)
    (erstes,) = lade_hoch(anna, "a.txt").json()
    r = anna.post(
        "/api/dokumente/upload",
        files=[("dateien", ("b.txt", b"B.", "text/plain")), ("dateien", ("c.txt", b"C.", "text/plain"))],
    )
    assert r.status_code == 429
    assert "2 eigene Dokumente" in r.json()["detail"]
    assert "Löschen Sie ältere eigene Dokumente" in r.json()["detail"]
    assert lade_hoch(anna, "b.txt").status_code == 201
    assert anna.post("/api/dokumente", json={"titel": "c", "text": "C."}).status_code == 429
    assert lade_hoch(besucher(anna), "x.txt").status_code == 201

    assert anna.delete(f"/api/dokumente/{erstes['id']}").status_code == 204
    assert lade_hoch(anna, "c.txt").status_code == 201


def test_zu_langes_dokument_wird_vor_dem_embedding_abgelehnt(baue, embedder):
    class ZaehlenderEmbedder:
        name = embedder.name
        dimension = embedder.dimension
        aufrufe = 0

        def embed(self, texte):
            ZaehlenderEmbedder.aufrufe += 1
            return embedder.embed(texte)

        embed_query = embedder.embed_query

    client = baue(embedder_=ZaehlenderEmbedder(), absaetze_pro_dokument=3)
    r = lade_hoch(client, "lang.txt", "Eins.\n\nZwei.\n\nDrei.\n\nVier.")
    assert r.status_code == 413
    assert "«lang.txt»" in r.json()["detail"] and "3 Absätze" in r.json()["detail"]
    assert ZaehlenderEmbedder.aufrufe == 0
    assert client.get("/api/info").json()["uploads_heute"] == 0
    assert lade_hoch(client, "kurz.txt", "Eins.\n\nZwei.\n\nDrei.").status_code == 201


def test_tageslimit_uploads_gilt_fuer_alle(baue, uhr):
    anna = baue(uploads_pro_tag=2)
    bert = besucher(anna)
    assert lade_hoch(anna, "a.txt").status_code == 201
    assert lade_hoch(bert, "b.txt").status_code == 201
    r = lade_hoch(anna, "c.txt")
    assert r.status_code == 429
    assert "Tageslimit der Demo erreicht" in r.json()["detail"]
    uhr.vor(days=1)
    assert lade_hoch(anna, "c.txt").status_code == 201


def test_frage_und_k_sind_begrenzt(baue):
    client = baue()
    assert client.post("/api/frage", json={"frage": "x" * 501}).status_code == 422
    assert client.post("/api/frage", json={"frage": "Was?", "k": 11}).status_code == 422
    assert client.get("/api/suche", params={"q": "Was?", "k": 11}).status_code == 422


def test_info_nennt_die_zaehler_fuer_den_tagescheck(baue):
    client = baue(fragen_pro_tag=50)
    lade_hoch(client, "a.txt")
    lade_hoch(client, "b.txt")
    client.post("/api/frage", json={"frage": "Was?"})
    info = client.get("/api/info").json()
    assert info["fragen_heute"] == 1
    assert info["limit_fragen_pro_tag"] == 50
    assert info["uploads_heute"] == 2
    assert info["anzahl_dokumente"] == 2
