"""Die PDF-Fassungen der Beispieldokumente: Skript scripts/beispiel_pdfs.py und eingecheckte Dateien."""

from pathlib import Path

import pytest

from app.chunking import in_absaetze
from app.dateien import text_aus_pdf
from scripts.beispiel_pdfs import BEISPIELE_ORDNER, pdf_aus_markdown

MARKDOWN = """# Prüfbericht Straße 5 (fiktiv)

Die Größe der Öffnung beträgt 40 cm; Maße außen: 1.2 m. Ärger gibt es bei Übermaß.

Zweiter Absatz mit «Anführungszeichen» – und Gedankenstrich.
"""


def ohne_umbrueche(text: str) -> str:
    return " ".join(text.split())


def test_pdf_aus_markdown_erhaelt_umlaute_und_eszett():
    pdf = pdf_aus_markdown(MARKDOWN)
    assert pdf.startswith(b"%PDF-")
    text = ohne_umbrueche(text_aus_pdf(pdf))
    assert "Prüfbericht Straße 5 (fiktiv)" in text
    assert "Die Größe der Öffnung beträgt 40 cm; Maße außen: 1.2 m. Ärger gibt es bei Übermaß." in text
    assert "«Anführungszeichen» – und Gedankenstrich." in text
    assert "#" not in text


def test_pdf_aus_markdown_trennt_absaetze_fuer_das_chunking():
    # mehrzeilige Absätze wie in den Beispieltexten; Einzeiler gelten als weiter Zeilenabstand
    markdown = "# Titel\n\n" + "Erster Absatz mit mehreren Zeilen. " * 8 + "\n\n" + "Zweiter Absatz, ebenfalls lang. " * 8
    absaetze = in_absaetze(text_aus_pdf(pdf_aus_markdown(markdown)))
    assert len(absaetze) == 3
    assert absaetze[0] == "Titel"
    assert absaetze[2].startswith("Zweiter Absatz")


@pytest.mark.parametrize("md", sorted(BEISPIELE_ORDNER.glob("*.md")), ids=lambda p: p.stem)
def test_eingecheckte_pdf_entspricht_dem_markdown(md: Path):
    pdf = md.with_suffix(".pdf")
    assert pdf.is_file(), f"{pdf.name} fehlt: uv run python scripts/beispiel_pdfs.py"
    text = ohne_umbrueche(text_aus_pdf(pdf.read_bytes()))
    for absatz in md.read_text(encoding="utf-8").split("\n\n"):
        erwartet = ohne_umbrueche(absatz.lstrip("# "))
        assert erwartet in text
    assert len(in_absaetze(text_aus_pdf(pdf.read_bytes()))) == len(in_absaetze(md.read_text(encoding="utf-8")))
