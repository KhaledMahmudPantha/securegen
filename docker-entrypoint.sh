#!/bin/sh
# Builds the retrieval index (if not already built) before starting the
# API server, then hands off to whatever CMD was passed.
set -e

if [ ! -d "/app/data/index" ] || [ -z "$(ls -A /app/data/index 2>/dev/null)" ]; then
    if [ "$FETCH_REAL_CORPUS" = "1" ]; then
        echo "Building index from the real OWASP corpus (requires network)..."
        python scripts/build_index.py --fetch
    else
        echo "Building index from the offline sample corpus..."
        python scripts/build_index.py
    fi
fi

# Respect a platform-provided PORT (Render, HF Spaces, etc. all set this)
# and override whatever port the CMD hardcoded, so the same image works
# unmodified across hosts that assign different ports.
if [ -n "$PORT" ]; then
    set -- uvicorn api.main:app --host 0.0.0.0 --port "$PORT"
fi

exec "$@"
