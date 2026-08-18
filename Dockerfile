# SecureGen — Java security-code evaluator + RAG grounding, as a service.
#
# Build:
#   docker build -t securegen .
#
# Run (build the offline sample index at container start, since this
# Dockerfile doesn't assume network access at build time):
#   docker run -p 8000:8000 securegen
#
# Run with the real OWASP corpus (needs network at container start):
#   docker run -p 8000:8000 -e FETCH_REAL_CORPUS=1 securegen

FROM python:3.11-slim

# javac is required for the compile-gate step in securegen_eval.
# openjdk-17-jdk-headless matches the capstone's Java 17 compile target.
RUN apt-get update \
    && apt-get install -y --no-install-recommends openjdk-17-jdk-headless \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir fastapi "uvicorn[standard]"

COPY . .

# Build the retrieval index at container start (offline sample corpus by
# default; set FETCH_REAL_CORPUS=1 to pull the real OWASP corpus, which
# needs network access at that point).
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
