#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -d backend/.venv ]; then
  python3 -m venv backend/.venv
fi
backend/.venv/bin/pip install -r backend/requirements.txt

cd frontend
npm ci
npm run build
