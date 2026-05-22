#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/backend"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
BENCHMARK_ASSET_DATA_DIR="${BENCHMARK_ASSET_DATA_DIR:-/data/benchmarkAsset}"
RELOAD=0
export HOST PORT BENCHMARK_ASSET_DATA_DIR RELOAD

exec .venv/bin/uvicorn main:app --host "$HOST" --port "$PORT"
