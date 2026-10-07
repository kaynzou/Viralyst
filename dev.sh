#!/usr/bin/env bash
# Start Viralyst: the Python API (port 8000) and the website (port 3000).
# Press Ctrl+C once to stop both.
set -e
cd "$(dirname "$0")"

[ -d frontend/node_modules ] || (cd frontend && npm install)  # first time only

trap 'kill 0' EXIT  # when this script stops, stop everything it started
(cd backend && uv run fastapi dev viralyst/api.py --port 8000) &
(cd frontend && npm run dev) &
echo "Viralyst is starting. Open http://localhost:3000"
wait
