"""Text aus hochgeladenen Dateien holen: PDF (pypdf), TXT, MD."""

from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PyPdfError

ERLAUBTE_ENDUNGEN = ("pdf", "txt", "md")
MAX_BYTES = 20 * 1024 * 1024


class DateiFehler(ValueError):
    pass


def text_aus_pdf(daten: bytes) -> str:
    """Seitentexte, durch Leerzeilen getrennt, damit das Chunking Seiten als Absätze erkennt."""
    try:
        reader = PdfReader(BytesIO(daten))
        seiten = [(seite.extract_text() or "").strip() for seite in reader.pages]
    except (PyPdfError, ValueError, TypeError) as e:
        raise DateiFehler(f"PDF konnte nicht gelesen werden: {e}") from e
    return "\n\n".join(s for s in seiten if s)


def text_aus_datei(dateiname: str, daten: bytes) -> str:
    endung = dateiname.rsplit(".", 1)[-1].lower() if "." in dateiname else ""
    if endung not in ERLAUBTE_ENDUNGEN:
        raise DateiFehler(f"Nur {', '.join(ERLAUBTE_ENDUNGEN)} sind erlaubt, nicht «{dateiname}»")
    if endung == "pdf":
        return text_aus_pdf(daten)
    return daten.decode("utf-8", errors="replace")
