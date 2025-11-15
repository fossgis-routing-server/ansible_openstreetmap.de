#!/usr/bin/env bash
set -eo pipefail

umask 022

source /venv/bin/activate

# collect static files
umap collectstatic --noinput

# now wait for the database
umap wait_for_database

# then migrate the database
umap migrate

# run the server
# Use Unix Domain Socket if SOCKET_PATH is set, otherwise use HTTP
if [ -n "$SOCKET_PATH" ]; then
    echo "Starting uMap with Unix Domain Socket: $SOCKET_PATH"
    exec uvicorn --proxy-headers --no-access-log --uds "$SOCKET_PATH" umap.asgi:application
else
    echo "Starting uMap with HTTP on host 0.0.0.0:${PORT:-8000}"
    exec uvicorn --proxy-headers --no-access-log --host 0.0.0.0 --port "${PORT:-8000}" umap.asgi:application
fi
