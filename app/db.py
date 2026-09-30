"""PostgreSQL-Zugriff mit psycopg 3 und pgvector."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import psycopg
from pgvector.psycopg import register_vector

SCHEMA_DATEI = Path(__file__).resolve().parent.parent / "sql" / "001_schema.sql"


@dataclass(frozen=True)
class Treffer:
    titel: str
    absatz: str
    score: float


@dataclass(frozen=True)
class Dokument:
    id: int
    titel: str
    anzahl_absaetze: int
    erstellt: datetime


class DimensionKonflikt(RuntimeError):
    pass


def gespeicherte_dimension(url: str) -> int | None:
    """Dimension der Spalte absaetze.embedding, None wenn die Tabelle fehlt."""
    with psycopg.connect(url) as conn:
        zeile = conn.execute(
            """
            SELECT a.atttypmod FROM pg_attribute a
            JOIN pg_class c ON c.oid = a.attrelid
            WHERE c.relname = 'absaetze' AND a.attname = 'embedding'
            """
        ).fetchone()
    return int(zeile[0]) if zeile else None


def migriere(url: str, dimension: int) -> None:
    """Schema anlegen, idempotent. Einmal beim Start aufrufen, vor verbinde()."""
    vorhanden = gespeicherte_dimension(url)
    if vorhanden is not None and vorhanden != dimension:
        raise DimensionKonflikt(
            f"Die Datenbank hat Vektoren mit {vorhanden} Dimensionen, der konfigurierte Embedder liefert "
            f"{dimension}. Entweder EMBED_PROVIDER/EMBED_MODEL/EMBED_DIM zurückstellen oder die Daten löschen "
            f"(docker compose down -v)."
        )
    with psycopg.connect(url) as conn:
        conn.execute(SCHEMA_DATEI.read_text().replace("{dimension}", str(dimension)))
        conn.commit()


def verbinde(url: str) -> psycopg.Connection:
    """Verbindung mit registriertem vector-Typ; setzt die Migration voraus."""
    conn = psycopg.connect(url)
    register_vector(conn)
    return conn


def speichere_dokument(
    conn: psycopg.Connection, titel: str, absaetze: list[str], embeddings: list[np.ndarray]
) -> int:
    if len(absaetze) != len(embeddings):
        raise ValueError("Anzahl Absätze und Embeddings stimmt nicht überein")
    with conn.transaction():
        (dok_id,) = conn.execute(
            "INSERT INTO dokumente (titel) VALUES (%s) RETURNING id", (titel,)
        ).fetchone()
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO absaetze (dokument_id, position, inhalt, embedding) VALUES (%s, %s, %s, %s)",
                [(dok_id, i, text, emb) for i, (text, emb) in enumerate(zip(absaetze, embeddings))],
            )
    return dok_id


def liste_dokumente(conn: psycopg.Connection) -> list[Dokument]:
    zeilen = conn.execute(
        """
        SELECT d.id, d.titel, count(a.id), d.erstellt_am
        FROM dokumente d LEFT JOIN absaetze a ON a.dokument_id = d.id
        GROUP BY d.id ORDER BY d.id
        """
    ).fetchall()
    return [Dokument(id=i, titel=t, anzahl_absaetze=int(n), erstellt=e) for i, t, n, e in zeilen]


def anzahl_dokumente(conn: psycopg.Connection) -> int:
    return int(conn.execute("SELECT count(*) FROM dokumente").fetchone()[0])


def titel_existiert(conn: psycopg.Connection, titel: str) -> bool:
    return conn.execute("SELECT 1 FROM dokumente WHERE titel = %s LIMIT 1", (titel,)).fetchone() is not None


def loesche_dokument(conn: psycopg.Connection, dok_id: int) -> bool:
    with conn.transaction():
        cur = conn.execute("DELETE FROM dokumente WHERE id = %s", (dok_id,))
        return cur.rowcount > 0


def suche(conn: psycopg.Connection, query_embedding: np.ndarray, k: int) -> list[Treffer]:
    # <=> ist die Cosinus-Distanz (0 = identisch, 2 = entgegengesetzt);
    # Score = 1 - Distanz ergibt die Cosinus-Ähnlichkeit in [-1, 1].
    zeilen = conn.execute(
        """
        SELECT d.titel, a.inhalt, 1 - (a.embedding <=> %(q)s) AS score
        FROM absaetze a
        JOIN dokumente d ON d.id = a.dokument_id
        ORDER BY a.embedding <=> %(q)s
        LIMIT %(k)s
        """,
        {"q": query_embedding, "k": k},
    ).fetchall()
    return [Treffer(titel=t, absatz=a, score=float(s)) for t, a, s in zeilen]
