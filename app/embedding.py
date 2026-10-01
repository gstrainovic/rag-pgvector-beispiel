"""Embeddings: über eine OpenAI-kompatible API (Ollama lokal, Mistral, OpenAI) oder lokal per fastembed.

Konfiguration über die Umgebung (siehe .env.example):
- EMBED_PROVIDER  ollama (Standard) | openai | fastembed
- EMBED_MODEL     Modellname beim Anbieter
- EMBED_DIM       Vektordimension; fehlt sie, wird sie per Probeanfrage ermittelt
- EMBED_BASE_URL, EMBED_API_KEY   nur nötig, wenn Embeddings von einem anderen Dienst als das LLM kommen
"""

import os
from typing import Protocol

import httpx
import numpy as np

from app.anbieter import KONTINGENT_STATUS, AnbieterKontingent

OLLAMA_LOKAL = "http://localhost:11434/v1"
OLLAMA_EMBED_MODELL = "qwen3-embedding:0.6b"
FASTEMBED_MODELL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


class Embedder(Protocol):
    name: str
    dimension: int

    def embed(self, texte: list[str]) -> list[np.ndarray]: ...

    def embed_query(self, texte: list[str]) -> list[np.ndarray]: ...


class OpenAiKompatiblerEmbedder:
    """POST {basis_url}/embeddings mit {"model", "input": [...]}; liefert normierte float32-Vektoren."""

    def __init__(
        self,
        basis_url: str,
        api_key: str,
        modell: str,
        client: httpx.Client | None = None,
        dimension_vorgabe: int | None = None,
        stapelgroesse: int = 32,
    ):
        self.basis_url = basis_url.rstrip("/")
        self.api_key = api_key
        self.modell = modell
        self.name = modell
        self._client = client or httpx.Client(timeout=120)
        self._dimension = dimension_vorgabe
        self._stapelgroesse = stapelgroesse

    @property
    def dimension(self) -> int:
        if self._dimension is None:
            (probe,) = self.embed(["Probe"])
            self._dimension = int(probe.shape[0])
        return self._dimension

    def embed(self, texte: list[str]) -> list[np.ndarray]:
        vektoren: list[np.ndarray] = []
        for i in range(0, len(texte), self._stapelgroesse):
            vektoren.extend(self._anfrage(texte[i : i + self._stapelgroesse]))
        return vektoren

    def embed_query(self, texte: list[str]) -> list[np.ndarray]:
        return self.embed(texte)

    def _anfrage(self, texte: list[str]) -> list[np.ndarray]:
        try:
            r = self._client.post(
                f"{self.basis_url}/embeddings",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.modell, "input": texte},
            )
        except httpx.TransportError as e:
            raise RuntimeError(f"Embedding-Dienst {self.basis_url} nicht erreichbar: {e}") from e
        if r.status_code == 404:
            raise RuntimeError(
                f"Embedding-Modell «{self.modell}» fehlt beim Dienst {self.basis_url} ({r.text[:200]}). "
                f"Bei Ollama: ollama pull qwen3-embedding:0.6b und "
                f"ollama create qwen3-embedding-cpu -f ollama/Modelfile.qwen3-embedding-cpu"
            )
        if r.status_code in KONTINGENT_STATUS:
            raise AnbieterKontingent(f"Embedding-Dienst antwortet mit {r.status_code}: {r.text[:300]}")
        if r.status_code >= 400:
            raise RuntimeError(f"Embedding-Dienst antwortet mit {r.status_code}: {r.text[:300]}")
        daten = sorted(r.json()["data"], key=lambda d: d.get("index", 0))
        return [_normiere(np.asarray(d["embedding"], dtype=np.float32)) for d in daten]


class FastembedEmbedder:
    """Lokal auf der CPU (ONNX), ohne Ollama. Modell ~220 MB, 384 Dimensionen, ~50 Sprachen."""

    dimension = 384

    def __init__(self, cache_dir: str | None = None):
        from fastembed import TextEmbedding  # optionale Abhängigkeit, erst hier laden

        cache_dir = cache_dir or os.environ.get("FASTEMBED_CACHE_PATH")
        self._modell = TextEmbedding(model_name=FASTEMBED_MODELL, cache_dir=cache_dir)
        self.name = f"fastembed:{FASTEMBED_MODELL.split('/')[-1]}"

    def embed(self, texte: list[str]) -> list[np.ndarray]:
        return [_normiere(v) for v in self._modell.embed(texte)]

    def embed_query(self, texte: list[str]) -> list[np.ndarray]:
        return [_normiere(v) for v in self._modell.query_embed(texte)]


def _normiere(v: np.ndarray) -> np.ndarray:
    return v / np.linalg.norm(v)


def aus_umgebung() -> Embedder:
    provider = os.environ.get("EMBED_PROVIDER", "ollama").lower()
    dimension = int(os.environ["EMBED_DIM"]) if os.environ.get("EMBED_DIM") else None

    if provider == "fastembed":
        return FastembedEmbedder()

    if provider == "ollama":
        basis_url = os.environ.get("EMBED_BASE_URL") or os.environ.get("LLM_BASE_URL") or OLLAMA_LOKAL
        api_key = os.environ.get("EMBED_API_KEY") or os.environ.get("LLM_API_KEY") or "ollama"
        modell = os.environ.get("EMBED_MODEL", OLLAMA_EMBED_MODELL)
        return OpenAiKompatiblerEmbedder(basis_url, api_key, modell, dimension_vorgabe=dimension)

    if provider == "openai":
        basis_url = os.environ.get("EMBED_BASE_URL") or os.environ.get("LLM_BASE_URL")
        api_key = os.environ.get("EMBED_API_KEY") or os.environ.get("LLM_API_KEY")
        modell = os.environ.get("EMBED_MODEL")
        if not basis_url or not api_key or not modell:
            raise RuntimeError(
                "EMBED_PROVIDER=openai braucht LLM_BASE_URL und LLM_API_KEY (oder EMBED_BASE_URL/EMBED_API_KEY) "
                "sowie EMBED_MODEL"
            )
        return OpenAiKompatiblerEmbedder(basis_url, api_key, modell, dimension_vorgabe=dimension)

    raise RuntimeError(f"Unbekannter EMBED_PROVIDER «{provider}», erlaubt: ollama, openai, fastembed")
