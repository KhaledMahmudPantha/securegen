"""
api/main.py
------------
FastAPI wrapper exposing the SecureGen pipeline as a service:

    POST /scan       - evaluate a Java source string against a task
    GET  /tasks       - list available task ids
    POST /guidance    - retrieve grounding guidance for a task prompt

Run locally:
    uvicorn api.main:app --reload

Run in Docker: see Dockerfile at repo root.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from securegen_eval.pipeline import evaluate_java_source  # noqa: E402
from securegen_eval.tasks import list_task_ids  # noqa: E402
from securegen_rag.retriever import Retriever  # noqa: E402

app = FastAPI(
    title="SecureGen API",
    description="Evaluate AI-generated Java security code and retrieve grounding guidance.",
    version="0.1.0",
)

_INDEX_DIR = Path(__file__).resolve().parents[1] / "data" / "index"
_retriever: Retriever | None = None


def _get_retriever() -> Retriever:
    global _retriever
    if _retriever is None:
        if not _INDEX_DIR.exists():
            raise HTTPException(
                status_code=503,
                detail="RAG index not built yet. Run `python scripts/build_index.py` at startup.",
            )
        _retriever = Retriever.load(_INDEX_DIR)
    return _retriever


class ScanRequest(BaseModel):
    task_id: str
    java_code: str
    already_clean: bool = True


class GuidanceRequest(BaseModel):
    task_prompt: str
    top_k: int = 3


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/tasks")
def tasks() -> dict:
    return {"tasks": list_task_ids()}


@app.post("/scan")
def scan(req: ScanRequest) -> dict:
    try:
        result = evaluate_java_source(req.task_id, req.java_code, already_clean=req.already_clean)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result


@app.post("/guidance")
def guidance(req: GuidanceRequest) -> dict:
    retriever = _get_retriever()
    items = retriever.guidance_for_task(req.task_prompt, top_k=req.top_k)
    return {
        "task_prompt": req.task_prompt,
        "guidance": [{"text": g.text, "source": g.source, "score": g.score} for g in items],
    }
