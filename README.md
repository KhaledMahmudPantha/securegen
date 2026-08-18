# SecureGen

A deployed tool that evaluates whether AI-generated Java security code
(crypto/TLS) actually behaves securely — not just whether it compiles —
grounded in retrieved documentation rather than a fixed prompt snippet.

This project extends the capstone **"Evaluating Docs-Grounded StarCoder2
for Java Security API Misuse"** into a public, deployable artifact. The
capstone proved the evaluation *methodology* works; this project turns
that methodology into something a recruiter, interviewer, or another
developer can actually run.

## What it does

Given a Java source file and a task ID (e.g. `aes_gcm_encrypt`,
`tls_min_12`), SecureGen tells you:

1. **Does it compile?** (`javac` gate)
2. **Does it actually attempt the task?** (task-adequacy checks — a
   compiled empty shell doesn't count)
3. **Is it secure?** (regex-based misuse detectors for known bad
   patterns — weak IVs, MD5/SHA-1, permissive TLS, weak PBKDF2 iteration
   counts, etc.)
4. **What does official guidance say about this task?** (RAG retrieval
   over OWASP Cheat Sheets / Oracle docs — dynamically retrieved per
   task, not a fixed snippet)

Final verdict: `SECURE`, `MISUSE`, `COMPILED_SEMANTIC_FAIL`, or
`UNCOMPILED` — the same four-way label scheme the capstone used.

## Project status (what's real vs. scaffolded)

| Phase | Status | Notes |
|---|---|---|
| 1 — RAG retrieval layer | **Built & tested** | TF-IDF retrieval verified end-to-end against a sample corpus. Real OWASP corpus fetcher written but needs to be run somewhere with network access (not this dev sandbox). |
| 2 — Eval pipeline as a package | **Built & tested** | Same detection logic as the capstone notebook, moved into `securegen_eval/` with a CLI. Detector/semantic tests pass. Compile-gate tests are structurally correct but **could not be run in this sandbox — no `javac` here.** Run `pytest` somewhere with a JDK to confirm. |
| 3 — Docker + API | **Written, not yet run** | Dockerfile + FastAPI app are complete and syntax-checked, but **not build-tested** — this sandbox has no Docker and no network for `apt-get`/`pip install fastapi`. Build and run this yourself before trusting it fully; see "Known gaps" below. |
| 4 — Write-up / comparison | **Not started** | This is your next step once Phase 1's real corpus is wired into your capstone notebook — see "Suggested next experiment". |

I'm flagging this precisely instead of just saying "it's done" — Phases
1–2 are genuinely verified with passing tests; Phase 3 is complete code
that I could not execute in this environment, so treat it as a strong
first draft to build and debug locally, not as pre-verified.

## Repo layout

```
securegen/
├── securegen_rag/       # Phase 1: RAG retrieval (chunker, embedder, vector store, retriever)
├── securegen_eval/       # Phase 2: eval pipeline (tasks, compiler, detectors, semantics, CLI)
├── api/main.py            # Phase 3: FastAPI app wiring both together
├── Dockerfile              # Phase 3: deployment
├── docker-entrypoint.sh
├── scripts/
│   ├── build_index.py     # build the RAG index (offline sample or --fetch real corpus)
│   └── query_demo.py      # CLI demo for retrieval
├── data/
│   ├── sample_corpus/     # small offline placeholder corpus (paraphrased, not OWASP text)
│   ├── corpus/             # real corpus lands here after --fetch (gitignored)
│   └── index/               # built vector index (gitignored)
├── examples/
│   └── SecureAesGcm.java  # example file for testing the CLI
├── tests/
│   ├── test_rag_pipeline.py
│   └── test_eval_pipeline.py
└── requirements.txt
```

## Quickstart (local, offline-capable parts)

```bash
pip install -r requirements.txt

# Phase 1: build the retrieval index (offline sample corpus, works right now)
python scripts/build_index.py
python scripts/query_demo.py

# Phase 2: list tasks, scan a Java file
python -m securegen_eval.cli list-tasks
python -m securegen_eval.cli scan examples/SecureAesGcm.java --task aes_gcm_encrypt
```

**The `scan` command needs a JDK on PATH** (`javac`) to actually compile
the file — install one locally (`sudo apt install openjdk-17-jdk` /
`brew install openjdk@17`) or just use Docker, which installs it for you.

## Running with Docker (Phase 3)

```bash
docker build -t securegen .
docker run -p 8000:8000 securegen
# then:
curl http://localhost:8000/health
curl http://localhost:8000/tasks
```

To use the real OWASP corpus instead of the offline sample (needs
network access when the container starts):

```bash
docker run -p 8000:8000 -e FETCH_REAL_CORPUS=1 securegen
```

**I have not been able to build/run this image myself** — no Docker
daemon and no network in the sandbox I built this in. Build it locally
first and fix anything that comes up before you demo or deploy it; the
most likely rough edges are apt/pip version pinning and the entrypoint
script's permissions on your OS.

### API endpoints

- `GET /health` — liveness check
- `GET /tasks` — list task ids
- `POST /scan` — `{"task_id": "aes_gcm_encrypt", "java_code": "..."}` → full verdict
- `POST /guidance` — `{"task_prompt": "...", "top_k": 3}` → retrieved guidance chunks

## Using the real OWASP corpus

```bash
python scripts/build_index.py --fetch   # needs network — run locally, Colab, or Kaggle
```

See `securegen_rag/fetch_corpus.py` for exactly what it pulls (OWASP
Cheat Sheet Series markdown, direct from GitHub, at build time — nothing
vendored in this repo).

## Plugging retrieval into the capstone notebook

In the capstone's `build_requirement_block()`:

```python
from securegen_rag import Retriever
_retriever = Retriever.load("data/index")

if condition == "docs_grounded":
    lines.append("Short guidance:")
    for x in _retriever.as_prompt_lines(task["prompt"], top_k=3):
        lines.append(f"- {x}")
```

Everything downstream (compile gate, misuse detectors, semantic checks)
is unchanged, which keeps this comparable to the capstone's existing
baseline/risky branches.

## Suggested next experiment (Phase 4)

Re-run the capstone's Run-C-style evaluation with the `docs_grounded`
branch pointed at retrieved guidance instead of the static
`task["doc_snippet"]`. The capstone found static docs-grounding
improved task adequacy but not secure rate — the open question this
answers: is that a property of documentation grounding in general, or
an artifact of the snippet being fixed rather than retrieved per task?
Write the result up (a short blog post or repo write-up) alongside a
link to the live Docker/API demo — that combination (novel finding +
working deployed tool) is a strong portfolio piece.

## Known gaps / what to check before showing this to anyone

- **Compile-gate tests are unverified in this build environment** — no
  `javac` here. Run `pytest tests/` somewhere with a JDK before relying
  on them.
- **Docker image is unbuilt/untested** — no Docker daemon or network
  here. Build it locally and work through any dependency issues.
- **Misuse detectors are regex-based**, inherited as-is from the
  capstone — same known limitation the capstone report flags: they
  catch anticipated patterns, not semantically-equivalent misuse
  phrased differently. A stratified manual audit is still the right
  next step before treating detector output as ground truth.
- **The real OWASP corpus has not actually been fetched and compared**
  against the capstone's static snippets yet — that comparison is the
  Phase 4 write-up, still to do.

## License / attribution note

OWASP Cheat Sheet Series content is fetched at build time under its own
license (CC BY-SA) directly from the OWASP GitHub repo — not vendored
or redistributed here. `data/sample_corpus/` files are original,
paraphrased summaries written for offline testing only.
