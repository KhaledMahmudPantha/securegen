#!/usr/bin/env python3
"""
query_demo.py — quick demo: given a task-style prompt, show what
guidance the retriever pulls, in the exact shape that plugs into the
capstone's prompt builder ("Short guidance:" lines).

Example:
    python scripts/query_demo.py "Encrypt plaintext using AES-GCM with a random IV"
    python scripts/query_demo.py "Restrict TLS to secure protocol versions only"
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from securegen_rag.retriever import Retriever  # noqa: E402

DEFAULT_QUERIES = [
    "Encrypt plaintext using AES-GCM with a random initialization vector.",
    "Derive a password hash using PBKDF2 with strong settings.",
    "Restrict a TLS server to secure protocol versions only.",
    "Restrict TLS cipher suites to strong, forward-secret choices.",
]


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    index_dir = root / "data" / "index"
    if not index_dir.exists():
        print("No index found. Run `python scripts/build_index.py` first.")
        sys.exit(1)

    retriever = Retriever.load(index_dir)

    queries = sys.argv[1:] or DEFAULT_QUERIES
    for q in queries:
        print("=" * 78)
        print("TASK PROMPT:", q)
        print("-" * 78)
        for line in retriever.as_prompt_lines(q, top_k=3):
            print(" -", line)
        print()


if __name__ == "__main__":
    main()
