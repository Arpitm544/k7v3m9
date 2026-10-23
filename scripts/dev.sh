#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
if [ ! -x .venv/bin/python ] || [ ! -d frontend/node_modules ]; then
    echo 'Install the dependencies first using the README instructions.' >&2
    exit 1
fi
.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 &
api_pid=$!
cleanup() { kill "$api_pid" 2>/dev/null || true; }
trap cleanup EXIT INT TERM
npm run dev --prefix frontend -- --host 127.0.0.1
