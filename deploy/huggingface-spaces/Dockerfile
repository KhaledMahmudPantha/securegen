# Dockerfile for Hugging Face Spaces (Docker SDK).
#
# Differences from the main /Dockerfile at repo root:
#   - Listens on port 7860 (Spaces' required port) instead of 8000
#   - Sets HOME and writable permissions the way Spaces' container
#     user expects (Spaces runs containers as a non-root "user" account)
#
# Deploy: put THIS file (renamed to just "Dockerfile") plus the rest of
# the securegen project files (securegen_rag/, securegen_eval/, api/,
# scripts/, data/, requirements.txt, docker-entrypoint.sh) at the ROOT
# of your Space's file list — see deploy/huggingface-spaces/README.md
# in this folder for exact upload instructions.

FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends openjdk-17-jdk-headless \
    && rm -rf /var/lib/apt/lists/*

# Hugging Face Spaces runs the container as a non-root user — create
# one explicitly and own /app, so pip/index-building work without
# permission errors.
RUN useradd -m -u 1000 spaceuser
WORKDIR /app
RUN chown -R spaceuser:spaceuser /app

COPY --chown=spaceuser:spaceuser requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir fastapi "uvicorn[standard]"

COPY --chown=spaceuser:spaceuser . .
RUN chmod +x /app/docker-entrypoint.sh

USER spaceuser
ENV HOME=/home/spaceuser

EXPOSE 7860
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "7860"]
