import numpy as np

from app.embedding import DIMENSION


def test_dimension_passt_zum_modell(embedder):
    (vektor,) = embedder.embed(["Hallo Welt"])
    assert len(vektor) == DIMENSION


def test_vektoren_sind_normiert(embedder):
    (vektor,) = embedder.embed(["Ein normierter Vektor"])
    assert abs(float(np.linalg.norm(vektor)) - 1.0) < 1e-3


def test_deutsch_semantisch_nah(embedder):
    hund, katze, steuer = embedder.embed(
        ["Der Hund bellt im Garten.", "Die Katze schläft auf dem Sofa.", "Die Steuererklärung ist fällig."]
    )
    (frage,) = embedder.embed_query(["Welches Tier bellt?"])
    assert np.dot(frage, hund) > np.dot(frage, steuer)
    assert np.dot(hund, katze) > np.dot(hund, steuer)
