"""
chunker.py
----------
Splits a document's raw text into overlapping chunks suitable for
embedding + retrieval. Chunking by paragraph/heading first, then
falling back to a sliding window, keeps each chunk topically coherent
(important for short cheat-sheet style docs where a single paragraph
often IS the complete guidance for one rule).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


@dataclass
class Chunk:
    doc_id: str
    source: str
    chunk_id: str
    text: str
    metadata: dict = field(default_factory=dict)


def _split_paragraphs(text: str) -> list[str]:
    # Split on blank lines / markdown headings, drop empties.
    parts = re.split(r"\n\s*\n|\n(?=#{1,6}\s)", text)
    return [p.strip() for p in parts if p.strip()]


def _sliding_window(paragraphs: list[str], max_chars: int, overlap_chars: int) -> list[str]:
    """Greedily pack paragraphs into ~max_chars chunks with a bit of overlap."""
    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) + 1 <= max_chars:
            current = f"{current}\n{para}".strip()
        else:
            if current:
                chunks.append(current)
            # start new chunk, optionally carrying a short overlap tail
            tail = current[-overlap_chars:] if overlap_chars and current else ""
            current = f"{tail}\n{para}".strip() if tail else para
            # if a single paragraph is itself bigger than max_chars, hard-split it
            while len(current) > max_chars:
                chunks.append(current[:max_chars])
                current = current[max_chars - overlap_chars:]
    if current:
        chunks.append(current)
    return chunks


def _is_low_quality_chunk(text: str, min_chars: int = 150) -> bool:
    """
    Filters out chunks that would win a retrieval slot on keyword overlap
    alone despite carrying little real guidance:

    - Markdown table separator/divider rows (e.g. "---|---|---"), which
      are almost pure punctuation and match broadly against anything.
    - Tiny "this page has moved / is deprecated" stub pages — real
      content is elsewhere, so these are near-noise in a retrieval index.
    - Any chunk under min_chars after collapsing whitespace, since a
      genuinely useful guidance chunk is rarely that short.
    """
    stripped = " ".join(text.split())
    if len(stripped) < min_chars:
        return True

    # Table separator rows: strip common table/markdown punctuation and
    # see what's left. If almost nothing alphanumeric remains, it's noise.
    alnum_only = re.sub(r'[^A-Za-z0-9]', '', stripped)
    if len(alnum_only) < 20:
        return True

    lowered = stripped.lower()
    if ("has been moved" in lowered or "has been deprecated" in lowered or "please visit" in lowered) and len(stripped) < 300:
        return True

    return False


def chunk_text(
    text: str,
    doc_id: str,
    source: str,
    max_chars: int = 900,
    overlap_chars: int = 120,
    extra_metadata: dict | None = None,
) -> list[Chunk]:
    paragraphs = _split_paragraphs(text)
    if not paragraphs:
        return []
    raw_chunks = _sliding_window(paragraphs, max_chars=max_chars, overlap_chars=overlap_chars)
    out = []
    for i, c in enumerate(raw_chunks):
        if _is_low_quality_chunk(c):
            continue
        out.append(
            Chunk(
                doc_id=doc_id,
                source=source,
                chunk_id=f"{doc_id}::chunk{i:03d}",
                text=c,
                metadata=dict(extra_metadata or {}),
            )
        )
    return out


def chunk_file(path: Path, source: str | None = None, **kwargs) -> list[Chunk]:
    path = Path(path)
    text = path.read_text(encoding="utf-8", errors="ignore")
    return chunk_text(
        text,
        doc_id=path.stem,
        source=source or str(path),
        **kwargs,
    )


def chunk_directory(directory: Path, glob: str = "*.md", **kwargs) -> Iterable[Chunk]:
    directory = Path(directory)
    for path in sorted(directory.glob(glob)):
        yield from chunk_file(path, **kwargs)
