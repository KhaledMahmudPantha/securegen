"""
retriever.py
------------
High-level "given a Java security task, get grounding guidance" API.
This is the piece that replaces the capstone's fixed `doc_snippet`
per task with real retrieval.

Usage
-----
    from securegen_rag import Retriever

    r = Retriever.load("data/index")
    guidance = r.guidance_for_task(
        task_prompt="Encrypt plaintext using AES-GCM with a random 96-bit IV.",
        top_k=3,
    )
    for g in guidance:
        print(g.source, g.score)
        print(g.text)

`guidance_for_task` returns short, citation-carrying snippets ready to
be dropped into the same "Short guidance:" prompt slot the capstone's
`build_requirement_block()` already uses for the docs_grounded branch —
so swapping static -> dynamic grounding is a small change in the
prompt builder, not a rewrite of the generation pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .embed_store import TfidfEmbedder, VectorStore


@dataclass
class Guidance:
    text: str
    source: str
    score: float


class Retriever:
    def __init__(self, store: VectorStore):
        self.store = store

    @classmethod
    def build_from_directory(cls, corpus_dir: Path, index_dir: Path | None = None) -> "Retriever":
        from .chunker import chunk_directory

        chunks = list(chunk_directory(Path(corpus_dir), glob="*.md"))
        if not chunks:
            raise ValueError(
                f"No .md files found in {corpus_dir}. "
                "Run scripts/build_index.py --fetch first, or point at data/sample_corpus."
            )
        store = VectorStore(TfidfEmbedder())
        store.build(chunks)
        if index_dir is not None:
            store.save(Path(index_dir))
        return cls(store)

    @classmethod
    def load(cls, index_dir: Path) -> "Retriever":
        store = VectorStore.load(Path(index_dir))
        return cls(store)

    def guidance_for_task(self, task_prompt: str, top_k: int = 3, min_score: float = 0.0) -> list[Guidance]:
        results = self.store.query(task_prompt, top_k=top_k)
        return [
            Guidance(text=chunk.text, source=chunk.source, score=score)
            for chunk, score in results
            if score >= min_score
        ]

    def as_prompt_lines(self, task_prompt: str, top_k: int = 3) -> list[str]:
        """
        Convenience wrapper matching the capstone's existing prompt-builder
        shape: a flat list of short guidance lines, e.g. for
        `build_requirement_block()`'s "Short guidance:" section.
        """
        lines = []
        for g in self.guidance_for_task(task_prompt, top_k=top_k):
            snippet = " ".join(g.text.split())  # collapse whitespace
            if len(snippet) > 220:
                snippet = snippet[:217] + "..."
            lines.append(f"{snippet} (source: {g.source})")
        return lines
