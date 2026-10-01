import json

import httpx
import pytest

from app.llm import SYSTEM_PROMPT, OpenAiKompatiblerAntwortgeber, aus_umgebung


def sse(*zeilen: str) -> str:
    return "".join(f"data: {z}\n\n" for z in zeilen)


def chunk(text: str) -> str:
    return json.dumps({"choices": [{"delta": {"content": text}}]})


@pytest.fixture
def stream_adapter():
    empfangen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        empfangen["url"] = str(request.url)
        empfangen["auth"] = request.headers.get("authorization")
        empfangen["body"] = json.loads(request.content)
        koerper = sse(
            json.dumps({"choices": [{"delta": {"role": "assistant"}}]}),
            chunk("Der "),
            chunk("Hund."),
            json.dumps({"choices": [{"delta": {}, "finish_reason": "stop"}]}),
            "[DONE]",
        )
        return httpx.Response(200, content=koerper.encode(), headers={"content-type": "text/event-stream"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    adapter = OpenAiKompatiblerAntwortgeber(
        basis_url="https://llm.example/v1", api_key="geheim", modell="test-modell", client=client
    )
    return adapter, empfangen


def test_adapter_streamt_tokens_aus_sse(stream_adapter):
    adapter, empfangen = stream_adapter

    tokens = list(adapter.antworte_stream("Welches Tier bellt?", ["Der Hund bellt.", "Die Katze schläft."]))

    assert tokens == ["Der ", "Hund."]
    assert empfangen["url"] == "https://llm.example/v1/chat/completions"
    assert empfangen["auth"] == "Bearer geheim"
    body = empfangen["body"]
    assert body["model"] == "test-modell"
    assert body["stream"] is True
    assert "reasoning_effort" not in body
    assert body["max_tokens"] == 500  # Antwortlänge gedeckelt: die Demo ist öffentlich
    nachrichten = body["messages"]
    assert nachrichten[0] == {"role": "system", "content": SYSTEM_PROMPT}
    assert nachrichten[-1]["role"] == "user"
    assert "Welches Tier bellt?" in nachrichten[-1]["content"]
    assert "[1] Der Hund bellt." in nachrichten[-1]["content"]
    assert "[2] Die Katze schläft." in nachrichten[-1]["content"]


def test_antworte_sammelt_den_stream_zu_einem_text(stream_adapter):
    adapter, _ = stream_adapter
    assert adapter.antworte("Welches Tier bellt?", ["Der Hund bellt."]) == "Der Hund."


def test_reasoning_effort_wird_nur_auf_wunsch_mitgeschickt():
    empfangen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        empfangen["body"] = json.loads(request.content)
        return httpx.Response(200, content=sse(chunk("Ok"), "[DONE]").encode())

    adapter = OpenAiKompatiblerAntwortgeber(
        "https://llm.example/v1", "k", "m", client=httpx.Client(transport=httpx.MockTransport(handler)),
        reasoning_effort="none",
    )
    list(adapter.antworte_stream("Frage?", ["Kontext"]))
    assert empfangen["body"]["reasoning_effort"] == "none"


def test_systemprompt_ist_deutsch_und_verlangt_quellentreue():
    assert "Absätze" in SYSTEM_PROMPT or "Absaetze" in SYSTEM_PROMPT
    assert "nicht in den Dokumenten" in SYSTEM_PROMPT
    assert "Sprache der Frage" in SYSTEM_PROMPT


def test_aus_umgebung_standard_ist_ollama_lokal(monkeypatch):
    for v in ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL", "LLM_REASONING_EFFORT"):
        monkeypatch.delenv(v, raising=False)
    adapter = aus_umgebung()
    assert adapter.basis_url == "http://localhost:11434/v1"
    assert adapter.modell == "qwen3:4b-instruct-2507-q4_K_M"


def test_aus_umgebung_mit_cloud_dienst(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "k")
    monkeypatch.setenv("LLM_BASE_URL", "https://api.mistral.ai/v1/")
    monkeypatch.setenv("LLM_MODEL", "mistral-small-latest")
    monkeypatch.setenv("LLM_REASONING_EFFORT", "none")
    adapter = aus_umgebung()
    assert adapter.basis_url == "https://api.mistral.ai/v1"
    assert adapter.modell == "mistral-small-latest"
    assert adapter.reasoning_effort == "none"
    assert adapter.max_tokens == 500


def test_max_tokens_aus_der_umgebung(monkeypatch):
    monkeypatch.setenv("LLM_MAX_TOKENS", "120")
    assert aus_umgebung().max_tokens == 120
