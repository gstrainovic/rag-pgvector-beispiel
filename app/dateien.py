"""Text aus hochgeladenen Dateien holen: PDF (pypdf), TXT, MD."""

import re
from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PyPdfError

ERLAUBTE_ENDUNGEN = ("pdf", "txt", "md")
MAX_BYTES = 20 * 1024 * 1024


class DateiFehler(ValueError):
    pass


def text_aus_pdf(daten: bytes) -> str:
    """Text mit Leerzeilen zwischen Absätzen (und zwischen Seiten), so wie das Chunking ihn erwartet."""
    try:
        reader = PdfReader(BytesIO(daten))
        seiten = [_seitentext(seite) for seite in reader.pages]
    except (PyPdfError, ValueError, TypeError) as e:
        raise DateiFehler(f"PDF konnte nicht gelesen werden: {e}") from e
    return "\n\n".join(s for s in seiten if s)


def _seitentext(seite) -> str:
    """Der Layout-Modus von pypdf setzt Leerzeilen, wo im Satz ein Absatzabstand steht.

    Bei weitem Zeilenabstand hält er jede Zeile für einen Absatz; dann gilt die Seite als ein Block.
    """
    einfach = (seite.extract_text() or "").strip()
    try:
        layout = seite.extract_text(extraction_mode="layout") or ""
    except Exception:  # noqa: BLE001 – der Layout-Modus ist Zugabe, der einfache Text reicht
        return einfach
    bloecke = [[z.strip() for z in b.splitlines() if z.strip()] for b in re.split(r"\n\s*\n", layout)]
    bloecke = [b for b in bloecke if b]
    zeilen = sum(len(b) for b in bloecke)
    if len(bloecke) < 2 or zeilen < 1.5 * len(bloecke):
        return einfach
    return "\n\n".join("\n".join(b) for b in bloecke)


def text_aus_datei(dateiname: str, daten: bytes) -> str:
    endung = dateiname.rsplit(".", 1)[-1].lower() if "." in dateiname else ""
    if endung not in ERLAUBTE_ENDUNGEN:
        raise DateiFehler(f"Nur {', '.join(ERLAUBTE_ENDUNGEN)} sind erlaubt, nicht «{dateiname}»")
    if endung == "pdf":
        return text_aus_pdf(daten)
    return daten.decode("utf-8", errors="replace")
