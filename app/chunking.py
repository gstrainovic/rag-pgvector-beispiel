"""Text in Absätze zerlegen (Chunking).

Regel: Leerzeilen trennen Absätze. Zu lange Absätze werden an Satzgrenzen
weiter geteilt, damit kein Chunk die Eingabegrenze des Embedding-Modells sprengt.
"""

import re

_SATZENDE = re.compile(r"(?<=[.!?])\s+")


def in_absaetze(text: str, max_zeichen: int = 1000) -> list[str]:
    absaetze = []
    for roh in re.split(r"\n\s*\n", text):
        absatz = " ".join(roh.split())
        if not absatz:
            continue
        absaetze.extend(_teile_langen_absatz(absatz, max_zeichen))
    return absaetze


def _teile_langen_absatz(absatz: str, max_zeichen: int) -> list[str]:
    if len(absatz) <= max_zeichen:
        return [absatz]
    teile: list[str] = []
    aktuell = ""
    for satz in _SATZENDE.split(absatz):
        kandidat = f"{aktuell} {satz}".strip()
        if aktuell and len(kandidat) > max_zeichen:
            teile.append(aktuell)
            aktuell = satz
        else:
            aktuell = kandidat
    if aktuell:
        teile.append(aktuell)
    return teile
