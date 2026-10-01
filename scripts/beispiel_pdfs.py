"""Erzeugt zu jedem Beispieltext in app/beispiele/ eine PDF-Fassung.

Einmalig bzw. nach Änderungen an den Markdown-Dateien ausführen, die PDFs werden eingecheckt:

    uv run python scripts/beispiel_pdfs.py

Die Beispieltexte bestehen nur aus einer Überschrift («# …») und Absätzen; mehr Markdown
versteht das Skript absichtlich nicht.
"""

from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate

BEISPIELE_ORDNER = Path(__file__).resolve().parent.parent / "app" / "beispiele"

# Helvetica ist eine der 14 Standardschriften (WinAnsi): Umlaute, ß, « » und – sind enthalten,
# es muss keine Schriftdatei eingebettet werden.
_TITEL = ParagraphStyle("titel", fontName="Helvetica-Bold", fontSize=16, leading=20, spaceAfter=14, alignment=TA_LEFT)
_ABSATZ = ParagraphStyle("absatz", fontName="Helvetica", fontSize=11, leading=15, spaceAfter=11, alignment=TA_LEFT)


def pdf_aus_markdown(markdown: str, titel: str = "") -> bytes:
    """Überschrift und Absätze als A4-PDF mit Textebene."""
    puffer = BytesIO()
    dokument = SimpleDocTemplate(
        puffer,
        pagesize=A4,
        leftMargin=25 * mm,
        rightMargin=25 * mm,
        topMargin=25 * mm,
        bottomMargin=25 * mm,
        title=titel,
        author="Strainovic IT",
        invariant=1,  # kein Erstellungsdatum: gleiche Eingabe ergibt dieselbe Datei
    )
    elemente = []
    for block in markdown.split("\n\n"):
        text = " ".join(block.split())
        if not text:
            continue
        if text.startswith("#"):
            elemente.append(Paragraph(escape(text.lstrip("# ")), _TITEL))
        else:
            elemente.append(Paragraph(escape(text), _ABSATZ))
    dokument.build(elemente)
    return puffer.getvalue()


def main() -> None:
    for md in sorted(BEISPIELE_ORDNER.glob("*.md")):
        ziel = md.with_suffix(".pdf")
        ziel.write_bytes(pdf_aus_markdown(md.read_text(encoding="utf-8"), titel=md.stem))
        print(f"{ziel.name}: {ziel.stat().st_size} Bytes")


if __name__ == "__main__":
    main()
