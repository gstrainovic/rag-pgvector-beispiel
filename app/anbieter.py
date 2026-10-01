"""Gemeinsames für die Aufrufe beim Modell-Anbieter (Sprachmodell und Embeddings)."""

# 402 Zahlung nötig, 403 Zugriff gesperrt, 429 Kontingent oder Ratenlimit erreicht. Mit einem
# Ausgabenlimit beim Anbieter ist das der erwartete Zustand, sobald das Kontingent aufgebraucht ist.
KONTINGENT_STATUS = (402, 403, 429)

KONTINGENT_MELDUNG = (
    "Die Demo hat ihr Monatskontingent beim Modell-Anbieter erreicht oder der Anbieter ist gerade ausgelastet. "
    "Bitte später noch einmal versuchen."
)


class AnbieterKontingent(RuntimeError):
    """Der Anbieter lehnt ab, weil Kontingent, Ausgabenlimit oder Ratenlimit des Kontos erreicht sind.

    Die Ausnahme trägt die Antwort des Anbieters für das Protokoll; Besucher sehen KONTINGENT_MELDUNG.
    """
