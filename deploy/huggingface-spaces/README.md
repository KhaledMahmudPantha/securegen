---
title: SecureGen
emoji: 🔒
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# SecureGen — deploying to Hugging Face Spaces

This file (with the YAML block above) is what Spaces reads to configure
your Space — **it must be named `README.md` and sit at the root of your
Space's files.**

## What to upload, and where

Your Space's root file list needs to look like this (flat structure,
not nested inside another `securegen/` folder):

```
README.md                    <- THIS file (rename it from this location)
Dockerfile                    <- the one in THIS folder (deploy/huggingface-spaces/Dockerfile)
docker-entrypoint.sh           <- from the project root
requirements.txt                <- from the project root
api/                              <- entire folder, from project root
securegen_rag/                     <- entire folder, from project root
securegen_eval/                     <- entire folder, from project root
scripts/                              <- entire folder, from project root
data/sample_corpus/                    <- just this subfolder (data/corpus and data/index are built at container start, don't upload them)
```

**Do NOT upload `data/corpus/` or `data/index/`** — those get built
automatically when the container starts (same as the local Docker
setup), and Spaces has a repo size limit that gitignored build
artifacts would eat into for no reason.

## Upload method (easiest): drag-and-drop in the browser

1. Create the Space (SDK: Docker) as described in the main chat message.
2. On your new Space's page, click the **"Files"** tab, then **"Add
   file" → "Upload files"**.
3. Drag in the files/folders listed above. For nested folders, most
   browsers let you drag a whole folder in at once and it preserves
   structure — if not, upload file-by-file into the right path using
   the "Add file" button repeatedly with the correct relative path
   typed into the filename box (e.g. `api/main.py`).
4. Once everything's uploaded, go to the **"App"** tab — the Space
   will start building automatically. This takes a few minutes (it's
   installing a JDK + Python deps + building the RAG index).

## After it builds

Your public URL will look like:
```
https://huggingface.co/spaces/<your-username>/securegen
```

Test it by visiting `<that-url>` — FastAPI's `/docs` page
(`<that-url>/docs` or the Space's embedded view) gives you an
interactive UI to try `/scan` and `/guidance` right in the browser,
no curl/Postman needed.

## If the build fails

Click the **"Logs"** tab on your Space — it shows the same kind of
output you saw in Colab (apt-get, pip install, etc.). Common issues:
- A file/folder was uploaded to the wrong path — check the tree above
- `requirements.txt` missing — re-upload it if the pip install step fails
- Build timing out on the free tier — rare for a project this size, but
  if it happens, remove the `--fetch` OWASP corpus option from
  `docker-entrypoint.sh` temptorarily so it only builds the small
  offline sample corpus at startup (much faster).
