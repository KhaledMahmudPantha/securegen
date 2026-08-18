#!/usr/bin/env python3
"""
build_index.py — build (or rebuild) the retrieval index.

Offline (default, works right now, no network needed):
    python scripts/build_index.py

With the real OWASP corpus (needs network — run locally/Colab/Kaggle):
    python scripts/build_index.py --fetch
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from securegen_rag.retriever import Retriever  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the securegen-rag retrieval index.")
    parser.add_argument(
        "--corpus",
        default=None,
        help="Directory of .md files to index. Defaults to data/corpus if it has files, "
        "otherwise falls back to data/sample_corpus (offline demo).",
    )
    parser.add_argument(
        "--index-out",
        default="data/index",
        help="Where to save the built index.",
    )
    parser.add_argument(
        "--fetch",
        action="store_true",
        help="Download the real OWASP Cheat Sheet corpus into data/corpus/ first (needs network).",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    corpus_dir = Path(args.corpus) if args.corpus else root / "data" / "corpus"

    if args.fetch:
        from securegen_rag.fetch_corpus import fetch_owasp_cheatsheets

        print("Fetching real OWASP corpus (requires network access)...")
        fetch_owasp_cheatsheets(corpus_dir)

    if not corpus_dir.exists() or not any(corpus_dir.glob("*.md")):
        print(f"No corpus found at {corpus_dir}, falling back to offline sample corpus.")
        corpus_dir = root / "data" / "sample_corpus"

    print(f"Indexing corpus from: {corpus_dir}")
    retriever = Retriever.build_from_directory(corpus_dir, index_dir=root / args.index_out)
    print(f"Indexed {len(retriever.store.chunks)} chunks -> saved to {root / args.index_out}")


if __name__ == "__main__":
    main()
