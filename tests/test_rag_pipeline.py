"""
End-to-end sanity tests for the securegen_rag scaffold.
Run with: pytest -q
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from securegen_rag.chunker import chunk_text
from securegen_rag.embed_store import TfidfEmbedder, VectorStore
from securegen_rag.retriever import Retriever

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_CORPUS = ROOT / "data" / "sample_corpus"


def test_chunk_text_produces_nonempty_chunks():
    text = "# Title\n\nParagraph one.\n\nParagraph two is here.\n\n## Subheading\n\nMore content."
    chunks = chunk_text(text, doc_id="doc1", source="unit-test", max_chars=50, overlap_chars=5)
    assert len(chunks) > 0
    assert all(c.text.strip() for c in chunks)
    assert all(c.doc_id == "doc1" for c in chunks)


def test_vector_store_returns_relevant_top_result():
    from securegen_rag.chunker import Chunk

    chunks = [
        Chunk(doc_id="a", source="a.md", chunk_id="a::0", text="AES-GCM requires a random initialization vector."),
        Chunk(doc_id="b", source="b.md", chunk_id="b::0", text="TLS 1.2 and 1.3 are the only acceptable protocol versions."),
        Chunk(doc_id="c", source="c.md", chunk_id="c::0", text="PBKDF2 iteration counts should be high to resist brute force."),
    ]
    store = VectorStore(TfidfEmbedder())
    store.build(chunks)

    results = store.query("What IV size should AES GCM use?", top_k=1)
    assert results[0][0].doc_id == "a"


def test_retriever_build_from_sample_corpus_and_query():
    retriever = Retriever.build_from_directory(SAMPLE_CORPUS)
    lines = retriever.as_prompt_lines("Restrict TLS to secure protocol versions", top_k=2)
    assert len(lines) == 2
    assert all(isinstance(line, str) and line for line in lines)


def test_save_and_load_index_roundtrip(tmp_path):
    index_dir = tmp_path / "index"
    retriever = Retriever.build_from_directory(SAMPLE_CORPUS, index_dir=index_dir)
    assert (index_dir / "matrix.npy").exists()
    assert (index_dir / "chunks.jsonl").exists()
    assert (index_dir / "tfidf_vectorizer.pkl").exists()

    loaded = Retriever.load(index_dir)
    lines = loaded.as_prompt_lines("password hashing", top_k=1)
    assert len(lines) == 1
