"""PostgreSQL-Zugriff mit psycopg 3 und pgvector.

Sichtbarkeit: Dokumente mit sitzung NULL sind Beispiele (für alle sichtbar, nicht löschbar),
alle anderen gehören der anonymen Sitzung, die sie hochgeladen hat. Jede Abfrage nimmt die
Sitzung des Aufrufers und sieht nur Beispiele plus Eigenes.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import numpy as np
import psycopg
from pgvector.psycopg import register_vector

SCHEMA_DATEI = Path(__file__).resolve().parent.parent / "sql" / "001_schema.sql"

_SICHTBAR = "(d.sitzung IS NULL OR d.sitzung = %(sitzung)s)"


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
    beispiel: bool


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
    # Die Suche filtert nach Sitzung. Ohne iterativen Scan (pgvector ab 0.8) prüft der HNSW-Index nur
    # seine ersten ef_search Kandidaten; gehören die alle anderen Besuchern, käme nichts zurück.
    conn.execute("SET hnsw.iterative_scan = strict_order")
    conn.commit()
    return conn


def speichere_dokument(
    conn: psycopg.Connection,
    titel: str,
    absaetze: list[str],
    embeddings: list[np.ndarray],
    sitzung: str | None = None,
) -> int:
    """Legt ein Dokument an; ohne Sitzung ist es ein Beispieldokument."""
    if len(absaetze) != len(embeddings):
        raise ValueError("Anzahl Absätze und Embeddings stimmt nicht überein")
    with conn.transaction():
        (dok_id,) = conn.execute(
            "INSERT INTO dokumente (titel, sitzung) VALUES (%s, %s) RETURNING id", (titel, sitzung)
        ).fetchone()
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO absaetze (dokument_id, position, inhalt, embedding) VALUES (%s, %s, %s, %s)",
                [(dok_id, i, text, emb) for i, (text, emb) in enumerate(zip(absaetze, embeddings))],
            )
    return dok_id


def liste_dokumente(conn: psycopg.Connection, sitzung: str | None = None) -> list[Dokument]:
    """Beispiele zuerst, danach die Dokumente der Sitzung in der Reihenfolge des Hochladens."""
    zeilen = conn.execute(
        f"""
        SELECT d.id, d.titel, count(a.id), d.erstellt_am, d.sitzung IS NULL
        FROM dokumente d LEFT JOIN absaetze a ON a.dokument_id = d.id
        WHERE {_SICHTBAR}
        GROUP BY d.id ORDER BY (d.sitzung IS NULL) DESC, d.id
        """,
        {"sitzung": sitzung},
    ).fetchall()
    return [Dokument(id=i, titel=t, anzahl_absaetze=int(n), erstellt=e, beispiel=b) for i, t, n, e, b in zeilen]


def anzahl_dokumente(conn: psycopg.Connection, sitzung: str | None = None) -> int:
    """Ohne Sitzung: alle Dokumente. Mit Sitzung: nur die eigenen (ohne Beispiele)."""
    if sitzung is None:
        return int(conn.execute("SELECT count(*) FROM dokumente").fetchone()[0])
    return int(conn.execute("SELECT count(*) FROM dokumente WHERE sitzung = %s", (sitzung,)).fetchone()[0])


def beispiel_titel(conn: psycopg.Connection) -> set[str]:
    return {t for (t,) in conn.execute("SELECT titel FROM dokumente WHERE sitzung IS NULL")}


def loesche_beispiele_ausser(conn: psycopg.Connection, titel: Iterable[str]) -> int:
    """Entfernt Dokumente ohne Sitzung, die kein aktuelles Beispiel sind (Bestand aus der Zeit vor den Sitzungen)."""
    with conn.transaction():
        cur = conn.execute("DELETE FROM dokumente WHERE sitzung IS NULL AND NOT (titel = ANY(%s))", (list(titel),))
        return cur.rowcount


def ist_beispiel(conn: psycopg.Connection, dok_id: int) -> bool:
    zeile = conn.execute("SELECT sitzung IS NULL FROM dokumente WHERE id = %s", (dok_id,)).fetchone()
    return bool(zeile and zeile[0])


def loesche_dokument(conn: psycopg.Connection, dok_id: int, sitzung: str | None = None) -> bool:
    """Löscht nur ein Dokument der angegebenen Sitzung; ohne Sitzung (nur intern) jedes Dokument."""
    with conn.transaction():
        if sitzung is None:
            cur = conn.execute("DELETE FROM dokumente WHERE id = %s", (dok_id,))
        else:
            cur = conn.execute("DELETE FROM dokumente WHERE id = %s AND sitzung = %s", (dok_id, sitzung))
        return cur.rowcount > 0


def loesche_abgelaufene(conn: psycopg.Connection, vor: datetime) -> int:
    """Löscht hochgeladene Dokumente, die vor dem Zeitpunkt angelegt wurden. Beispiele bleiben."""
    with conn.transaction():
        cur = conn.execute("DELETE FROM dokumente WHERE sitzung IS NOT NULL AND erstellt_am < %s", (vor,))
        return cur.rowcount


def suche(conn: psycopg.Connection, query_embedding: np.ndarray, k: int, sitzung: str | None = None) -> list[Treffer]:
    # <=> ist die Cosinus-Distanz (0 = identisch, 2 = entgegengesetzt);
    # Score = 1 - Distanz ergibt die Cosinus-Ähnlichkeit in [-1, 1].
    zeilen = conn.execute(
        f"""
        SELECT d.titel, a.inhalt, 1 - (a.embedding <=> %(q)s) AS score
        FROM absaetze a
        JOIN dokumente d ON d.id = a.dokument_id
        WHERE {_SICHTBAR}
        ORDER BY a.embedding <=> %(q)s
        LIMIT %(k)s
        """,
        {"q": query_embedding, "k": k, "sitzung": sitzung},
    ).fetchall()
    return [Treffer(titel=t, absatz=a, score=float(s)) for t, a, s in zeilen]


def erhoehe_zaehler(conn: psycopg.Connection, tag: date, name: str, limit: int, um: int = 1) -> bool:
    """Zählt atomar hoch, solange das Limit danach nicht überschritten ist. False = Limit erreicht."""
    if um > limit:
        return False
    with conn.transaction():
        zeile = conn.execute(
            """
            INSERT INTO tageszaehler (tag, name, wert) VALUES (%(tag)s, %(name)s, %(um)s)
            ON CONFLICT (tag, name) DO UPDATE SET wert = tageszaehler.wert + %(um)s
            WHERE tageszaehler.wert + %(um)s <= %(limit)s
            RETURNING wert
            """,
            {"tag": tag, "name": name, "um": um, "limit": limit},
        ).fetchone()
    return zeile is not None


def zaehlerstand(conn: psycopg.Connection, tag: date, name: str) -> int:
    zeile = conn.execute("SELECT wert FROM tageszaehler WHERE tag = %s AND name = %s", (tag, name)).fetchone()
    return int(zeile[0]) if zeile else 0
