import json

import httpx
import numpy as np
import pytest

from app.embedding import FastembedEmbedder, OpenAiKompatiblerEmbedder, aus_umgebung


def test_dimension_passt_zum_modell(embedder):
    (vektor,) = embedder.embed(["Hallo Welt"])
    assert len(vektor) == embedder.dimension == 384


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


def test_fastembed_hat_namen(embedder):
    assert embedder.name.startswith("fastembed:")


def _mock_embedder(dimension: int = 4, **kwargs):
    empfangen = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        empfangen.append((str(request.url), request.headers.get("authorization"), body))
        daten = [
            {"index": i, "embedding": [float(len(t))] + [0.0] * (dimension - 1)} for i, t in enumerate(body["input"])
        ]
        return httpx.Response(200, json={"data": daten, "model": body["model"]})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    emb = OpenAiKompatiblerEmbedder(
        "http://ollama:11434/v1/", "ollama", "qwen3-embedding:0.6b", client=client, **kwargs
    )
    return emb, empfangen


def test_openai_embedder_ruft_embeddings_endpunkt_und_normiert():
    emb, empfangen = _mock_embedder()
    a, b = emb.embed(["Hallo", "Hallo Welt"])
    url, auth, body = empfangen[0]
    assert url == "http://ollama:11434/v1/embeddings"
    assert auth == "Bearer ollama"
    assert body == {"model": "qwen3-embedding:0.6b", "input": ["Hallo", "Hallo Welt"]}
    assert abs(float(np.linalg.norm(a)) - 1.0) < 1e-6
    assert a.dtype == np.float32
    assert emb.embed_query(["x"])[0].shape == (4,)


def test_openai_embedder_ermittelt_dimension_per_probeanfrage():
    emb, empfangen = _mock_embedder(dimension=7)
    assert emb.dimension == 7
    assert emb.dimension == 7  # zweiter Zugriff ohne weitere Anfrage
    assert len(empfangen) == 1
    assert emb.name == "qwen3-embedding:0.6b"


def test_openai_embedder_nimmt_vorgegebene_dimension_ohne_anfrage():
    emb, empfangen = _mock_embedder(dimension=7, dimension_vorgabe=1024)
    assert emb.dimension == 1024
    assert empfangen == []


def test_openai_embedder_teilt_grosse_eingaben_in_stapel():
    emb, empfangen = _mock_embedder(stapelgroesse=3)
    vektoren = emb.embed([f"Text {i}" for i in range(7)])
    assert len(vektoren) == 7
    assert [len(b["input"]) for _, _, b in empfangen] == [3, 3, 1]


def _umgebung_leeren(monkeypatch):
    for v in ("EMBED_PROVIDER", "EMBED_MODEL", "EMBED_DIM", "EMBED_BASE_URL", "EMBED_API_KEY",
              "LLM_BASE_URL", "LLM_API_KEY"):
        monkeypatch.delenv(v, raising=False)


def test_aus_umgebung_standard_ist_ollama_lokal(monkeypatch):
    _umgebung_leeren(monkeypatch)
    emb = aus_umgebung()
    assert isinstance(emb, OpenAiKompatiblerEmbedder)
    assert emb.basis_url == "http://localhost:11434/v1"
    assert emb.modell == "qwen3-embedding:0.6b"


def test_aus_umgebung_ollama_folgt_llm_url(monkeypatch):
    _umgebung_leeren(monkeypatch)
    monkeypatch.setenv("EMBED_PROVIDER", "ollama")
    monkeypatch.setenv("LLM_BASE_URL", "http://ollama:11434/v1")
    emb = aus_umgebung()
    assert emb.basis_url == "http://ollama:11434/v1"


def test_aus_umgebung_openai_nimmt_llm_zugang_und_dimension(monkeypatch):
    _umgebung_leeren(monkeypatch)
    monkeypatch.setenv("EMBED_PROVIDER", "openai")
    monkeypatch.setenv("LLM_BASE_URL", "https://api.mistral.ai/v1")
    monkeypatch.setenv("LLM_API_KEY", "geheim")
    monkeypatch.setenv("EMBED_MODEL", "mistral-embed")
    monkeypatch.setenv("EMBED_DIM", "1024")
    emb = aus_umgebung()
    assert emb.basis_url == "https://api.mistral.ai/v1"
    assert emb.api_key == "geheim"
    assert emb.modell == "mistral-embed"
    assert emb.dimension == 1024


def test_aus_umgebung_openai_mit_eigener_embed_url(monkeypatch):
    _umgebung_leeren(monkeypatch)
    monkeypatch.setenv("EMBED_PROVIDER", "openai")
    monkeypatch.setenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
    monkeypatch.setenv("LLM_API_KEY", "g")
    monkeypatch.setenv("EMBED_BASE_URL", "https://api.openai.com/v1")
    monkeypatch.setenv("EMBED_API_KEY", "sk")
    monkeypatch.setenv("EMBED_MODEL", "text-embedding-3-small")
    emb = aus_umgebung()
    assert emb.basis_url == "https://api.openai.com/v1"
    assert emb.api_key == "sk"


def test_aus_umgebung_openai_ohne_schluessel_ist_fehler(monkeypatch):
    _umgebung_leeren(monkeypatch)
    monkeypatch.setenv("EMBED_PROVIDER", "openai")
    with pytest.raises(RuntimeError, match="LLM_API_KEY"):
        aus_umgebung()


def test_aus_umgebung_fastembed(monkeypatch):
    _umgebung_leeren(monkeypatch)
    monkeypatch.setenv("EMBED_PROVIDER", "fastembed")
    assert isinstance(aus_umgebung(), FastembedEmbedder)


def test_aus_umgebung_unbekannter_provider(monkeypatch):
    _umgebung_leeren(monkeypatch)
    monkeypatch.setenv("EMBED_PROVIDER", "cohere")
    with pytest.raises(RuntimeError, match="EMBED_PROVIDER"):
        aus_umgebung()
