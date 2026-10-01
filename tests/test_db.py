import psycopg
import pytest

from app import db


def test_migration_legt_extension_tabellen_und_hnsw_index_an(conn):
    ext = conn.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'").fetchone()
    assert ext is not None
    tabellen = {r[0] for r in conn.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")}
    assert {"dokumente", "absaetze"} <= tabellen
    indexdef = conn.execute(
        "SELECT indexdef FROM pg_indexes WHERE tablename = 'absaetze' AND indexdef ILIKE '%hnsw%'"
    ).fetchone()
    assert indexdef is not None
    assert "vector_cosine_ops" in indexdef[0]


def test_migration_ist_idempotent(datenbank_url):
    db.migriere(datenbank_url, dimension=384)
    db.migriere(datenbank_url, dimension=384)


def test_migration_mit_anderer_dimension_bei_bestehender_tabelle_ist_fehler(datenbank_url):
    with pytest.raises(db.DimensionKonflikt, match="384") as info:
        db.migriere(datenbank_url, dimension=1024)
    assert "1024" in str(info.value)
    assert "EMBED" in str(info.value)


def test_migration_legt_dimension_aus_parameter_an(datenbank_url):
    # eigene Datenbank, damit die Session-Datenbank mit 384 unberührt bleibt
    with psycopg.connect(datenbank_url, autocommit=True) as conn:
        conn.execute("DROP DATABASE IF EXISTS dim_test")
        conn.execute("CREATE DATABASE dim_test")
    url = datenbank_url.rsplit("/", 1)[0] + "/dim_test"
    db.migriere(url, dimension=1024)
    assert db.gespeicherte_dimension(url) == 1024


def test_speichern_und_suchen_mit_cosinus(conn, embedder):
    absaetze = [
        "Der Hund bellt im Garten.",
        "Die Steuererklärung ist bis Ende März fällig.",
        "Die Katze schläft auf dem Sofa.",
    ]
    dok_id = db.speichere_dokument(conn, "Alltag", absaetze, embedder.embed(absaetze))
    assert isinstance(dok_id, int)

    (frage,) = embedder.embed_query(["Welches Tier macht Lärm?"])
    treffer = db.suche(conn, frage, k=2)

    assert len(treffer) == 2
    assert treffer[0].titel == "Alltag"
    assert treffer[0].absatz == "Der Hund bellt im Garten."
    assert treffer[0].score >= treffer[1].score
    assert -1.0 <= treffer[1].score <= 1.0


def test_suche_in_leerer_datenbank_liefert_nichts(conn, embedder):
    (frage,) = embedder.embed_query(["irgendwas"])
    assert db.suche(conn, frage, k=5) == []


def test_k_begrenzt_treffer(conn, embedder):
    absaetze = [f"Absatz Nummer {i} über ganz verschiedene Dinge." for i in range(10)]
    db.speichere_dokument(conn, "Zehn", absaetze, embedder.embed(absaetze))
    (frage,) = embedder.embed_query(["Absatz"])
    assert len(db.suche(conn, frage, k=3)) == 3


def test_liste_dokumente_mit_anzahl_und_zeit(conn, embedder):
    a = ["Eins.", "Zwei."]
    b = ["Drei."]
    id_a = db.speichere_dokument(conn, "A", a, embedder.embed(a))
    id_b = db.speichere_dokument(conn, "B", b, embedder.embed(b))
    liste = db.liste_dokumente(conn)
    assert [(d.id, d.titel, d.anzahl_absaetze) for d in liste] == [(id_a, "A", 2), (id_b, "B", 1)]
    assert liste[0].erstellt is not None
    assert db.anzahl_dokumente(conn) == 2


def test_loesche_dokument_entfernt_auch_absaetze(conn, embedder):
    a = ["Eins.", "Zwei."]
    dok_id = db.speichere_dokument(conn, "A", a, embedder.embed(a))
    assert db.loesche_dokument(conn, dok_id) is True
    assert db.liste_dokumente(conn) == []
    assert conn.execute("SELECT count(*) FROM absaetze").fetchone()[0] == 0
    assert db.loesche_dokument(conn, dok_id) is False


# --- Sitzungen: Beispiele (sitzung NULL) und Dokumente je Besucher -----------------------------


def _dok(conn, embedder, titel, absaetze, sitzung=None):
    return db.speichere_dokument(conn, titel, absaetze, embedder.embed(absaetze), sitzung=sitzung)


def test_liste_zeigt_beispiele_zuerst_und_nur_die_eigene_sitzung(conn, embedder):
    eigen = _dok(conn, embedder, "Eigenes", ["Eins."], sitzung="anna")
    fremd = _dok(conn, embedder, "Fremdes", ["Zwei."], sitzung="bert")
    beispiel = _dok(conn, embedder, "Beispiel", ["Drei."])
    liste = db.liste_dokumente(conn, sitzung="anna")
    assert [(d.id, d.beispiel) for d in liste] == [(beispiel, True), (eigen, False)]
    assert [d.id for d in db.liste_dokumente(conn, sitzung="bert")] == [beispiel, fremd]
    assert [d.id for d in db.liste_dokumente(conn)] == [beispiel]
    assert db.anzahl_dokumente(conn) == 3
    assert db.anzahl_dokumente(conn, sitzung="anna") == 1


def test_suche_sieht_beispiele_und_eigene_aber_keine_fremden_dokumente(conn, embedder):
    _dok(conn, embedder, "Fremd", ["Der Hund bellt im Garten."], sitzung="bert")
    _dok(conn, embedder, "Eigen", ["Die Katze schläft auf dem Sofa."], sitzung="anna")
    _dok(conn, embedder, "Beispiel", ["Die Steuererklärung ist bis Ende März fällig."])
    (frage,) = embedder.embed_query(["Welches Tier bellt?"])
    assert {t.titel for t in db.suche(conn, frage, k=5, sitzung="anna")} == {"Eigen", "Beispiel"}
    assert db.suche(conn, frage, k=1, sitzung="bert")[0].titel == "Fremd"
    assert {t.titel for t in db.suche(conn, frage, k=5)} == {"Beispiel"}


def test_suche_findet_eigene_absaetze_auch_neben_vielen_fremden(conn, embedder):
    # Der HNSW-Index liefert zuerst die nächsten Nachbarn aller Besucher; der Filter darf die eigenen nicht verlieren
    fremd = [f"Der Hund Nummer {i} bellt laut im Garten." for i in range(120)]
    _dok(conn, embedder, "Fremd", fremd, sitzung="bert")
    _dok(conn, embedder, "Eigen", ["Die Steuererklärung ist bis Ende März fällig."], sitzung="anna")
    conn.execute("SET enable_seqscan = off")  # erzwingt den Index wie bei einer grossen Tabelle
    (frage,) = embedder.embed_query(["Welcher Hund bellt im Garten?"])
    assert [t.titel for t in db.suche(conn, frage, k=3, sitzung="anna")] == ["Eigen"]
    # Gegenprobe: ohne iterativen Scan bleibt der Filter nach den ersten 40 Kandidaten leer
    conn.execute("SET hnsw.iterative_scan = off")
    assert db.suche(conn, frage, k=3, sitzung="anna") == []


def test_loeschen_nur_in_der_eigenen_sitzung(conn, embedder):
    eigen = _dok(conn, embedder, "Eigen", ["Eins."], sitzung="anna")
    beispiel = _dok(conn, embedder, "Beispiel", ["Zwei."])
    assert db.loesche_dokument(conn, eigen, sitzung="bert") is False
    assert db.loesche_dokument(conn, beispiel, sitzung="anna") is False
    assert db.ist_beispiel(conn, beispiel) is True
    assert db.ist_beispiel(conn, eigen) is False
    assert db.ist_beispiel(conn, 999_999) is False
    assert db.loesche_dokument(conn, eigen, sitzung="anna") is True
    assert [d.id for d in db.liste_dokumente(conn, sitzung="anna")] == [beispiel]


def test_abgelaufene_uploads_werden_geloescht_beispiele_bleiben(conn, embedder):
    from datetime import UTC, datetime, timedelta

    alt = _dok(conn, embedder, "Alt", ["Eins."], sitzung="anna")
    neu = _dok(conn, embedder, "Neu", ["Zwei."], sitzung="anna")
    beispiel = _dok(conn, embedder, "Beispiel", ["Drei."])
    jetzt = datetime.now(UTC)
    conn.execute("UPDATE dokumente SET erstellt_am = %s WHERE id IN (%s, %s)", (jetzt - timedelta(hours=25), alt, beispiel))
    assert db.loesche_abgelaufene(conn, vor=jetzt - timedelta(hours=24)) == 1
    assert [d.id for d in db.liste_dokumente(conn, sitzung="anna")] == [beispiel, neu]
    assert conn.execute("SELECT count(*) FROM absaetze").fetchone()[0] == 2


def test_beispiele_abgleichen_entfernt_dokumente_ohne_sitzung_die_kein_beispiel_sind(conn, embedder):
    # Bestand aus der Zeit vor den Sitzungen: Uploads ohne Besitzer wären sonst für alle sichtbar und unlöschbar
    bleibt = _dok(conn, embedder, "Hausordnung Sonnenhof", ["Eins."])
    _dok(conn, embedder, "alter-upload.pdf", ["Zwei."])
    eigen = _dok(conn, embedder, "alter-upload.pdf", ["Drei."], sitzung="anna")
    assert db.loesche_beispiele_ausser(conn, ["Hausordnung Sonnenhof", "FAQ"]) == 1
    assert [d.id for d in db.liste_dokumente(conn, sitzung="anna")] == [bleibt, eigen]
    assert db.beispiel_titel(conn) == {"Hausordnung Sonnenhof"}


def test_migration_ergaenzt_die_spalte_sitzung_in_einer_bestehenden_datenbank(datenbank_url):
    with psycopg.connect(datenbank_url, autocommit=True) as conn:
        conn.execute("DROP DATABASE IF EXISTS alt_test")
        conn.execute("CREATE DATABASE alt_test")
    url = datenbank_url.rsplit("/", 1)[0] + "/alt_test"
    with psycopg.connect(url) as conn:
        conn.execute("CREATE EXTENSION vector")
        conn.execute("CREATE TABLE dokumente (id BIGSERIAL PRIMARY KEY, titel TEXT NOT NULL, erstellt_am TIMESTAMPTZ NOT NULL DEFAULT now())")
        conn.execute(
            "CREATE TABLE absaetze (id BIGSERIAL PRIMARY KEY, dokument_id BIGINT NOT NULL REFERENCES dokumente(id) "
            "ON DELETE CASCADE, position INTEGER NOT NULL, inhalt TEXT NOT NULL, embedding vector(384) NOT NULL)"
        )
        conn.execute("INSERT INTO dokumente (titel) VALUES ('Bestand')")
    db.migriere(url, dimension=384)
    with db.verbinde(url) as conn:
        (d,) = db.liste_dokumente(conn)
        assert (d.titel, d.beispiel) == ("Bestand", True)


# --- Tageszähler ------------------------------------------------------------------------------


def test_zaehler_zaehlt_bis_zum_limit_und_je_tag(conn):
    from datetime import date

    heute, morgen = date(2026, 10, 1), date(2026, 10, 2)
    assert db.zaehlerstand(conn, heute, "fragen") == 0
    assert db.erhoehe_zaehler(conn, heute, "fragen", limit=2) is True
    assert db.erhoehe_zaehler(conn, heute, "fragen", limit=2) is True
    assert db.erhoehe_zaehler(conn, heute, "fragen", limit=2) is False
    assert db.zaehlerstand(conn, heute, "fragen") == 2
    assert db.zaehlerstand(conn, heute, "uploads") == 0
    assert db.erhoehe_zaehler(conn, morgen, "fragen", limit=2) is True
    assert db.zaehlerstand(conn, morgen, "fragen") == 1


def test_zaehler_erhoeht_um_mehrere_nur_wenn_alle_platz_haben(conn):
    from datetime import date

    heute = date(2026, 10, 1)
    assert db.erhoehe_zaehler(conn, heute, "uploads", limit=5, um=3) is True
    assert db.erhoehe_zaehler(conn, heute, "uploads", limit=5, um=3) is False
    assert db.erhoehe_zaehler(conn, heute, "uploads", limit=5, um=2) is True
    assert db.zaehlerstand(conn, heute, "uploads") == 5
    assert db.erhoehe_zaehler(conn, heute, "leer", limit=0) is False
