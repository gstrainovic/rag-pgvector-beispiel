import re
from pathlib import Path

from app import db
from app.embedding import DIMENSION


def test_schema_dimension_stimmt_mit_modell_ueberein():
    sql = Path("sql/001_schema.sql").read_text()
    assert re.search(rf"vector\({DIMENSION}\)", sql)


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
    db.migriere(datenbank_url)
    db.migriere(datenbank_url)


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
