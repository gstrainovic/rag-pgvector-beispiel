import httpx
import pytest

from app.embedding import OpenAiKompatiblerEmbedder


def test_fehlendes_ollama_modell_gibt_verstaendliche_meldung():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": {"message": 'model "qwen3-embedding-cpu" not found, try pulling it first'}})

    emb = OpenAiKompatiblerEmbedder(
        "http://ollama:11434/v1", "ollama", "qwen3-embedding-cpu",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(RuntimeError) as info:
        emb.dimension
    meldung = str(info.value)
    assert "qwen3-embedding-cpu" in meldung
    assert "ollama pull" in meldung or "ollama create" in meldung
    assert "not found" in meldung


def test_nicht_erreichbarer_dienst_gibt_verstaendliche_meldung():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    emb = OpenAiKompatiblerEmbedder(
        "http://ollama:11434/v1", "ollama", "m", client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    with pytest.raises(RuntimeError, match="http://ollama:11434/v1 nicht erreichbar"):
        emb.embed(["x"])
