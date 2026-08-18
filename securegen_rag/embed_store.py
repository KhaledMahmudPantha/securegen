"""
embed_store.py
---------------
Embedding backends + a minimal vector store.

Two backends are provided behind the same interface:

* TfidfEmbedder            - zero-download, pure scikit-learn. Works
                              completely offline. This is the default,
                              so the whole pipeline runs with no network
                              access and no GPU.
* SentenceTransformerEmbedder - optional, higher-quality dense embeddings
                              (e.g. "all-MiniLM-L6-v2"). Requires
                              `pip install sentence-transformers` and a
                              one-time model download. Swap it in once
                              you're running this somewhere with network
                              access (e.g. not this sandboxed environment).

The VectorStore itself is backend-agnostic: it just stores vectors +
chunk metadata and does cosine-similarity top-k search with numpy, so
you don't need faiss/Chroma for a corpus this size (a few hundred to a
few thousand chunks). Swap in FAISS/Chroma later only if the corpus
grows past what fits comfortably in memory.
"""

from __future__ import annotations

import json
import pickle
from dataclasses import asdict
from pathlib import Path
from typing import Protocol

import numpy as np

from .chunker import Chunk


class Embedder(Protocol):
    def fit(self, texts: list[str]) -> None: ...
    def embed(self, texts: list[str]) -> np.ndarray: ...


class TfidfEmbedder:
    """
    Offline-friendly default embedder. TF-IDF + cosine similarity is a
    perfectly reasonable baseline for a focused, jargon-heavy corpus like
    security cheat sheets, where exact terminology (e.g. "GCMParameterSpec",
    "PBKDF2", "TLSv1.2") matters more than fuzzy semantic similarity.
    """

    def __init__(self, max_features: int = 20_000, ngram_range: tuple[int, int] = (1, 2)):
        from sklearn.feature_extraction.text import TfidfVectorizer

        self._vectorizer = TfidfVectorizer(
            max_features=max_features,
            ngram_range=ngram_range,
            stop_words="english",
        )
        self._fitted = False

    def fit(self, texts: list[str]) -> None:
        self._vectorizer.fit(texts)
        self._fitted = True

    def embed(self, texts: list[str]) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("TfidfEmbedder.fit() must be called before embed().")
        matrix = self._vectorizer.transform(texts)
        return matrix.toarray().astype(np.float32)

    def save(self, path: Path) -> None:
        with open(path, "wb") as f:
            pickle.dump(self._vectorizer, f)

    @classmethod
    def load(cls, path: Path) -> "TfidfEmbedder":
        obj = cls.__new__(cls)
        with open(path, "rb") as f:
            obj._vectorizer = pickle.load(f)
        obj._fitted = True
        return obj


class SentenceTransformerEmbedder:
    """
    Optional higher-quality embedder. Not used by default in this sandbox
    (no network to download model weights), but this is a drop-in swap:

        from securegen_rag.embed_store import SentenceTransformerEmbedder
        embedder = SentenceTransformerEmbedder("all-MiniLM-L6-v2")

    everywhere a TfidfEmbedder is used.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer  # optional dep

        self._model = SentenceTransformer(model_name)

    def fit(self, texts: list[str]) -> None:
        # Dense sentence-transformer models are pretrained; nothing to fit.
        return

    def embed(self, texts: list[str]) -> np.ndarray:
        return np.asarray(self._model.encode(texts, show_progress_bar=False), dtype=np.float32)


def _cosine_sim(query_vec: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    q = query_vec / (np.linalg.norm(query_vec, axis=-1, keepdims=True) + 1e-8)
    m = matrix / (np.linalg.norm(matrix, axis=-1, keepdims=True) + 1e-8)
    return m @ q.reshape(-1)


class VectorStore:
    """In-memory vector store with cosine similarity search + JSON/pickle persistence."""

    def __init__(self, embedder: Embedder):
        self.embedder = embedder
        self.chunks: list[Chunk] = []
        self.matrix: np.ndarray | None = None

    def build(self, chunks: list[Chunk]) -> None:
        self.chunks = chunks
        texts = [c.text for c in chunks]
        self.embedder.fit(texts)
        self.matrix = self.embedder.embed(texts)

    def query(self, text: str, top_k: int = 4) -> list[tuple[Chunk, float]]:
        if self.matrix is None or not self.chunks:
            raise RuntimeError("VectorStore is empty — call build() first, or load() a saved index.")
        q_vec = self.embedder.embed([text])[0]
        sims = _cosine_sim(q_vec, self.matrix)
        top_idx = np.argsort(-sims)[:top_k]
        return [(self.chunks[i], float(sims[i])) for i in top_idx]

    def save(self, directory: Path) -> None:
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        np.save(directory / "matrix.npy", self.matrix)
        with open(directory / "chunks.jsonl", "w", encoding="utf-8") as f:
            for c in self.chunks:
                f.write(json.dumps(asdict(c)) + "\n")
        if isinstance(self.embedder, TfidfEmbedder):
            self.embedder.save(directory / "tfidf_vectorizer.pkl")

    @classmethod
    def load(cls, directory: Path, embedder: Embedder | None = None) -> "VectorStore":
        directory = Path(directory)
        if embedder is None:
            embedder = TfidfEmbedder.load(directory / "tfidf_vectorizer.pkl")
        store = cls(embedder)
        store.matrix = np.load(directory / "matrix.npy")
        chunks = []
        with open(directory / "chunks.jsonl", encoding="utf-8") as f:
            for line in f:
                d = json.loads(line)
                chunks.append(Chunk(**d))
        store.chunks = chunks
        return store
