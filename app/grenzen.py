"""Grenzen der öffentlichen Demo: Sie läuft ohne Anmeldung, jede Frage und jeder Upload kostet beim Modellanbieter.

Besucher werden über ein anonymes Sitzungs-Cookie getrennt. Ein neuer Browser oder ein privates
Fenster ist ein neuer Besucher, darum gibt es zusätzlich globale Tagesgrenzen (Zähler in der
Datenbank, Tageswechsel nach UTC) und eine Grenze je Minute und IP-Adresse (im Speicher).
"""

import os
from collections import deque
from dataclasses import dataclass, fields
from datetime import datetime, timedelta
from threading import Lock


@dataclass(frozen=True)
class Grenzen:
    fragen_pro_tag: int = 300          # LIMIT_FRAGEN_PRO_TAG, global
    fragen_pro_minute_ip: int = 10     # LIMIT_FRAGEN_PRO_MINUTE_IP
    dokumente_pro_sitzung: int = 25    # LIMIT_DOKUMENTE_PRO_SITZUNG
    absaetze_pro_dokument: int = 200   # LIMIT_ABSAETZE_PRO_DOKUMENT
    uploads_pro_tag: int = 300         # LIMIT_UPLOADS_PRO_TAG, global
    lebensdauer_stunden: int = 24      # LIMIT_LEBENSDAUER_STUNDEN, danach werden Uploads gelöscht

    @classmethod
    def aus_umgebung(cls) -> "Grenzen":
        werte = {}
        for feld in fields(cls):
            roh = os.environ.get(f"LIMIT_{feld.name.upper()}", "").strip()
            if roh:
                werte[feld.name] = int(roh)
        return cls(**werte)


class MinutenFenster:
    """Gleitendes Fenster von 60 Sekunden je Schlüssel (IP-Adresse).

    Ein Prozess, darum reicht der Arbeitsspeicher. Adressen werden nirgends gespeichert oder
    protokolliert und fallen aus dem Speicher, sobald ihr letzter Eintrag älter als das Fenster ist.
    """

    def __init__(self, limit: int):
        self.limit = limit
        self._zeiten: dict[str, deque[datetime]] = {}
        self._sperre = Lock()  # Endpunkte laufen im Threadpool, die Wartung in einem eigenen Thread

    def erlaube(self, schluessel: str, jetzt: datetime) -> int:
        """0 = erlaubt und gezählt, sonst Sekunden bis zum nächsten freien Platz."""
        with self._sperre:
            self._saeubere(jetzt)
            zeiten = self._zeiten.get(schluessel)
            if zeiten and len(zeiten) >= self.limit:
                frei_ab = zeiten[0] + timedelta(seconds=60)
                return max(1, int((frei_ab - jetzt).total_seconds()) + 1)
            if self.limit < 1:
                return 60
            self._zeiten.setdefault(schluessel, deque()).append(jetzt)
            return 0

    def saeubere(self, jetzt: datetime) -> None:
        with self._sperre:
            self._saeubere(jetzt)

    def _saeubere(self, jetzt: datetime) -> None:
        grenze = jetzt - timedelta(seconds=60)
        for schluessel in list(self._zeiten):
            zeiten = self._zeiten[schluessel]
            while zeiten and zeiten[0] <= grenze:
                zeiten.popleft()
            if not zeiten:
                del self._zeiten[schluessel]

    def adressen(self) -> int:
        return len(self._zeiten)
