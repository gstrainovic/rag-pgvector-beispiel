"""Austauschbarer LLM-Adapter für POST /frage.

Der Dienst läuft ohne LLM (dann antwortet /frage mit 503). Wird LLM_BASE_URL
und LLM_API_KEY gesetzt, spricht der Adapter jede OpenAI-kompatible
Chat-Completions-API an (OpenAI, Mistral, Ollama lokal, ...).
"""

import os
from typing import Protocol

import httpx

SYSTEM_PROMPT = (
    "Du beantwortest Fragen ausschliesslich anhand des mitgelieferten Kontexts. "
    "Steht die Antwort nicht im Kontext, sag das klar. Antworte knapp und auf Deutsch."
)


class Antwortgeber(Protocol):
    def antworte(self, frage: str, kontexte: list[str]) -> str: ...


class OpenAiKompatiblerAntwortgeber:
    def __init__(self, basis_url: str, api_key: str, modell: str, client: httpx.Client | None = None):
        self.basis_url = basis_url.rstrip("/")
        self.modell = modell
        self._client = client or httpx.Client(timeout=60)
        self._headers = {"Authorization": f"Bearer {api_key}"}

    def antworte(self, frage: str, kontexte: list[str]) -> str:
        kontext_block = "\n\n".join(f"[{i + 1}] {k}" for i, k in enumerate(kontexte))
        nutzer = f"Kontext:\n{kontext_block}\n\nFrage: {frage}"
        r = self._client.post(
            f"{self.basis_url}/chat/completions",
            headers=self._headers,
            json={
                "model": self.modell,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": nutzer},
                ],
                "temperature": 0,
            },
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


def aus_umgebung() -> Antwortgeber | None:
    basis_url = os.environ.get("LLM_BASE_URL")
    api_key = os.environ.get("LLM_API_KEY")
    if not basis_url or not api_key:
        return None
    modell = os.environ.get("LLM_MODELL", "gpt-4o-mini")
    return OpenAiKompatiblerAntwortgeber(basis_url, api_key, modell)
