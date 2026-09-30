import json

import httpx

from app.llm import OpenAiKompatiblerAntwortgeber, aus_umgebung


def test_adapter_schickt_kontext_und_frage_und_liefert_antwort():
    empfangen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        empfangen["url"] = str(request.url)
        empfangen["auth"] = request.headers.get("authorization")
        empfangen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "Der Hund."}}]})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    adapter = OpenAiKompatiblerAntwortgeber(
        basis_url="https://llm.example/v1", api_key="geheim", modell="test-modell", client=client
    )

    antwort = adapter.antworte("Welches Tier bellt?", ["Der Hund bellt.", "Die Katze schläft."])

    assert antwort == "Der Hund."
    assert empfangen["url"] == "https://llm.example/v1/chat/completions"
    assert empfangen["auth"] == "Bearer geheim"
    assert empfangen["body"]["model"] == "test-modell"
    nachrichten = empfangen["body"]["messages"]
    assert nachrichten[-1]["role"] == "user"
    assert "Welches Tier bellt?" in nachrichten[-1]["content"]
    assert "Der Hund bellt." in nachrichten[-1]["content"]
    assert "Die Katze schläft." in nachrichten[-1]["content"]


def test_aus_umgebung_ohne_schluessel_gibt_none(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    assert aus_umgebung() is None


def test_aus_umgebung_mit_schluessel_und_url(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "k")
    monkeypatch.setenv("LLM_BASE_URL", "http://ollama:11434/v1")
    monkeypatch.setenv("LLM_MODELL", "llama3.2")
    adapter = aus_umgebung()
    assert isinstance(adapter, OpenAiKompatiblerAntwortgeber)
    assert adapter.modell == "llama3.2"
