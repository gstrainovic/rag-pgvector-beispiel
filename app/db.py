"""PostgreSQL-Zugriff mit psycopg 3 und pgvector."""

from dataclasses import dataclass
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


def migriere(url: str) -> None:
    """Schema anlegen, idempotent. Einmal beim Start aufrufen, vor verbinde()."""
    with psycopg.connect(url) as conn:
        conn.execute(SCHEMA_DATEI.read_text())
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
