"""Embeddings lokal mit fastembed (ONNX), ohne API-Schlüssel.

Modell: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
- ~50 Sprachen, darunter Deutsch
- 384 Dimensionen, ca. 220 MB, läuft auf CPU
- Vektoren werden hier normiert, daher Cosinus-Ähnlichkeit = Skalarprodukt
"""

import os
from typing import Protocol

import numpy as np
from fastembed import TextEmbedding

MODELL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DIMENSION = 384


class Embedder(Protocol):
    def embed(self, texte: list[str]) -> list[np.ndarray]: ...

    def embed_query(self, texte: list[str]) -> list[np.ndarray]: ...


class FastembedEmbedder:
    def __init__(self, cache_dir: str | None = None):
        cache_dir = cache_dir or os.environ.get("FASTEMBED_CACHE_PATH")
        self._modell = TextEmbedding(model_name=MODELL, cache_dir=cache_dir)

    def embed(self, texte: list[str]) -> list[np.ndarray]:
        return [_normiere(v) for v in self._modell.embed(texte)]

    def embed_query(self, texte: list[str]) -> list[np.ndarray]:
        return [_normiere(v) for v in self._modell.query_embed(texte)]


def _normiere(v: np.ndarray) -> np.ndarray:
    # fastembed liefert für dieses Modell unnormierte Vektoren (Mean Pooling).
    return v / np.linalg.norm(v)
