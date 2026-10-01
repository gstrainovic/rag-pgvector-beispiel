from app.chunking import in_absaetze


def test_leerzeilen_trennen_absaetze():
    text = "Erster Absatz.\n\nZweiter Absatz.\n\n\nDritter Absatz."
    assert in_absaetze(text) == ["Erster Absatz.", "Zweiter Absatz.", "Dritter Absatz."]


def test_zeilenumbrueche_innerhalb_eines_absatzes_werden_zu_leerzeichen():
    text = "Zeile eins\nZeile zwei\n\nNeuer Absatz"
    assert in_absaetze(text) == ["Zeile eins Zeile zwei", "Neuer Absatz"]


def test_leere_und_whitespace_absaetze_werden_verworfen():
    assert in_absaetze("\n\n   \n\nEinziger Absatz\n\n") == ["Einziger Absatz"]


def test_lange_absaetze_werden_an_satzgrenzen_geteilt():
    satz = "Das ist ein Satz mit einigen Wörtern drin. "
    text = satz * 40  # deutlich länger als die Obergrenze
    teile = in_absaetze(text, max_zeichen=300)
    assert len(teile) > 1
    assert all(len(t) <= 300 for t in teile)
    assert all(t.endswith(".") for t in teile)
    assert " ".join(teile) == text.strip()


def test_text_ohne_satzende_wird_hart_geteilt_damit_kein_absatz_die_obergrenze_sprengt():
    # z. B. eine Tabelle oder Datei ohne Punkte: die Obergrenze deckelt Tokens und damit Kosten je Absatz
    woerter = "wort " * 500 + "x" * 700
    teile = in_absaetze(woerter, max_zeichen=300)
    assert all(len(t) <= 300 for t in teile)
    assert "".join(teile).replace(" ", "") == woerter.replace(" ", "")
    assert teile[0].endswith("wort")  # wenn möglich an einer Wortgrenze
