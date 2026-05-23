#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/backend"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
RELOAD=0
export HOST PORT RELOAD

exec .venv/bin/uvicorn main:app --host "$HOST" --port "$PORT"
