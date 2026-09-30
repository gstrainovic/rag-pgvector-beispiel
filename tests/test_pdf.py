from io import BytesIO

import pytest
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app.dateien import DateiFehler, text_aus_datei, text_aus_pdf


def erzeuge_pdf(seiten: list[str]) -> bytes:
    puffer = BytesIO()
    c = canvas.Canvas(puffer, pagesize=A4)
    for seite in seiten:
        c.setFont("Helvetica", 12)
        c.drawString(72, 750, seite)
        c.showPage()
    c.save()
    return puffer.getvalue()


def test_text_aus_pdf_liefert_seiten_als_absaetze():
    pdf = erzeuge_pdf(["Erste Seite mit Umlauten: äöü.", "Zweite Seite."])
    text = text_aus_pdf(pdf)
    assert "Erste Seite mit Umlauten: äöü." in text
    assert "Zweite Seite." in text
    # Seiten sind durch eine Leerzeile getrennt, damit das Chunking sie als Absätze erkennt
    assert "\n\n" in text


def test_text_aus_datei_nach_endung():
    assert text_aus_datei("notiz.txt", b"Hallo Welt") == "Hallo Welt"
    assert text_aus_datei("notiz.MD", "# Titel\n\nAbsatz".encode()) == "# Titel\n\nAbsatz"
    pdf = erzeuge_pdf(["Aus der PDF."])
    assert "Aus der PDF." in text_aus_datei("scan.pdf", pdf)


def test_text_aus_datei_unbekannte_endung_wird_abgelehnt():
    with pytest.raises(DateiFehler, match="pdf, txt, md"):
        text_aus_datei("bild.png", b"\x89PNG")


def test_text_aus_datei_kaputte_pdf_wird_abgelehnt():
    with pytest.raises(DateiFehler, match="PDF"):
        text_aus_datei("kaputt.pdf", b"kein pdf")
