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

exec "$@"
