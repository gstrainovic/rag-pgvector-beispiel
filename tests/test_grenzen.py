from datetime import UTC, datetime, timedelta

from app.grenzen import MinutenFenster

START = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


def test_fenster_erlaubt_bis_zum_limit_und_nennt_die_wartezeit():
    fenster = MinutenFenster(limit=2)
    assert fenster.erlaube("a", START) == 0
    assert fenster.erlaube("a", START + timedelta(seconds=10)) == 0
    assert fenster.erlaube("a", START + timedelta(seconds=20)) == 41  # der erste Eintrag wird nach 60 s frei
    assert fenster.erlaube("b", START + timedelta(seconds=20)) == 0
    assert fenster.erlaube("a", START + timedelta(seconds=61)) == 0


def test_abgewiesene_anfragen_verlaengern_die_sperre_nicht():
    fenster = MinutenFenster(limit=1)
    fenster.erlaube("a", START)
    for s in range(1, 60):
        assert fenster.erlaube("a", START + timedelta(seconds=s)) > 0
    assert fenster.erlaube("a", START + timedelta(seconds=60)) == 0


def test_adressen_bleiben_nicht_laenger_als_das_fenster_im_speicher():
    # Die Datenschutzerklärung sagt zu, dass IP-Adressen nur kurz im Arbeitsspeicher liegen
    fenster = MinutenFenster(limit=5)
    fenster.erlaube("203.0.113.5", START)
    fenster.erlaube("198.51.100.7", START + timedelta(seconds=50))
    assert fenster.adressen() == 2
    fenster.saeubere(START + timedelta(seconds=61))
    assert fenster.adressen() == 1
    fenster.saeubere(START + timedelta(seconds=111))
    assert fenster.adressen() == 0


def test_jede_anfrage_raeumt_abgelaufene_adressen_mit_auf():
    fenster = MinutenFenster(limit=5)
    fenster.erlaube("203.0.113.5", START)
    fenster.erlaube("198.51.100.7", START + timedelta(seconds=120))
    assert fenster.adressen() == 1
