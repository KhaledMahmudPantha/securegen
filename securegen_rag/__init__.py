"""
securegen_rag
=============

A small, dependency-light Retrieval-Augmented Generation (RAG) layer for
grounding Java-security code generation/evaluation in real guidance
(OWASP Cheat Sheets, Oracle JCA/JSSE docs) instead of a fixed, hand-picked
snippet per task.

This package is designed to slot into the evaluation pipeline built for
the "Evaluating Docs-Grounded StarCoder2 for Java Security API Misuse"
capstone project: instead of a static doc_snippet per task, retrieve the
top-k most relevant guidance chunks at generation/evaluation time.

Modules
-------
chunker      - split raw documents into overlapping text chunks
embed_store  - embedding backends + a simple vector store (fit/query/save/load)
retriever    - high-level "given a task, get relevant guidance" API
fetch_corpus - pulls real OWASP Cheat Sheet + Oracle doc pages into data/corpus/
"""

from .retriever import Retriever  # noqa: F401
