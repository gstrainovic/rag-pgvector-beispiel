"""LLM-Adapter für POST /frage: OpenAI-kompatible Chat Completions mit Streaming.

Standard ohne Variablen: Ollama lokal (http://localhost:11434/v1) mit Qwen3-4B-Instruct-2507.
Über LLM_BASE_URL, LLM_API_KEY und LLM_MODEL läuft derselbe Adapter gegen Mistral, OpenAI
oder jeden anderen OpenAI-kompatiblen Dienst. Die Instruct-2507-Variante von Qwen3 hat keinen
Denkmodus; für Hybridmodelle (z. B. qwen3:4b) schaltet LLM_REASONING_EFFORT=none das Denken ab
(Ollama bildet «none» auf think=false ab). Nicht setzen, wenn der Dienst das Feld nicht kennt.
"""

import json
import os
from collections.abc import Iterator
from typing import Protocol

import httpx

from app.anbieter import KONTINGENT_STATUS, AnbieterKontingent

OLLAMA_LOKAL = "http://localhost:11434/v1"
STANDARD_MODELL = "qwen3:4b-instruct-2507-q4_K_M"
STANDARD_MAX_TOKENS = 500  # LLM_MAX_TOKENS: deckelt die Antwortlänge und damit die Kosten je Frage

SYSTEM_PROMPT = (
    "Du bist ein Assistent, der Fragen zu Dokumenten beantwortet. "
    "Du erhältst nummerierte Absätze aus den Dokumenten und eine Frage. "
    "Antworte ausschliesslich mit Informationen aus diesen Absätzen; erfinde nichts und nutze kein Wissen "
    "von ausserhalb. Steht die Antwort nicht in den Absätzen, schreib genau das: dass es nicht in den "
    "Dokumenten steht. Antworte knapp, in ganzen Sätzen und in der Sprache der Frage."
)


class Antwortgeber(Protocol):
    modell: str
    basis_url: str

    def antworte_stream(self, frage: str, kontexte: list[str]) -> Iterator[str]: ...


class OpenAiKompatiblerAntwortgeber:
    def __init__(
        self,
        basis_url: str,
        api_key: str,
        modell: str,
        client: httpx.Client | None = None,
        reasoning_effort: str | None = None,
        max_tokens: int = STANDARD_MAX_TOKENS,
    ):
        self.basis_url = basis_url.rstrip("/")
        self.modell = modell
        self.reasoning_effort = reasoning_effort
        self.max_tokens = max_tokens
        self._client = client or httpx.Client(timeout=httpx.Timeout(300, connect=10))
        self._headers = {"Authorization": f"Bearer {api_key}"}

    def antworte_stream(self, frage: str, kontexte: list[str]) -> Iterator[str]:
        kontext_block = "\n\n".join(f"[{i + 1}] {k}" for i, k in enumerate(kontexte))
        nutzer = f"Absätze aus den Dokumenten:\n\n{kontext_block}\n\nFrage: {frage}"
        body: dict = {
            "model": self.modell,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": nutzer},
            ],
            "temperature": 0,
            "max_tokens": self.max_tokens,
            "stream": True,
        }
        if self.reasoning_effort:
            body["reasoning_effort"] = self.reasoning_effort
        with self._client.stream(
            "POST", f"{self.basis_url}/chat/completions", headers=self._headers, json=body
        ) as r:
            if r.status_code >= 400:
                r.read()
                if r.status_code in KONTINGENT_STATUS:
                    raise AnbieterKontingent(f"LLM antwortet mit {r.status_code}: {r.text[:300]}")
                raise RuntimeError(f"LLM antwortet mit {r.status_code}: {r.text[:300]}")
            for zeile in r.iter_lines():
                if not zeile.startswith("data:"):
                    continue
                daten = zeile[5:].strip()
                if daten == "[DONE]":
                    break
                for choice in json.loads(daten).get("choices", []):
                    text = choice.get("delta", {}).get("content")
                    if text:
                        yield text

    def antworte(self, frage: str, kontexte: list[str]) -> str:
        return "".join(self.antworte_stream(frage, kontexte))


def aus_umgebung() -> OpenAiKompatiblerAntwortgeber:
    basis_url = os.environ.get("LLM_BASE_URL") or OLLAMA_LOKAL
    api_key = os.environ.get("LLM_API_KEY") or "ollama"  # Ollama verlangt einen Wert, ignoriert ihn aber
    modell = os.environ.get("LLM_MODEL") or STANDARD_MODELL
    return OpenAiKompatiblerAntwortgeber(
        basis_url,
        api_key,
        modell,
        reasoning_effort=os.environ.get("LLM_REASONING_EFFORT") or None,
        max_tokens=int(os.environ.get("LLM_MAX_TOKENS") or STANDARD_MAX_TOKENS),
    )
