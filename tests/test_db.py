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


def test_titel_existiert(conn, embedder):
    db.speichere_dokument(conn, "Hausordnung", ["x"], embedder.embed(["x"]))
    assert db.titel_existiert(conn, "Hausordnung") is True
    assert db.titel_existiert(conn, "Anderes") is False
