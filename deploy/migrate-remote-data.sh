#!/usr/bin/env bash
set -euo pipefail

REMOTE_HOST="${REMOTE_HOST:-115.190.185.17}"
REMOTE_USER="${REMOTE_USER:-root}"
SSH_KEY="${SSH_KEY:-}"
SSH_BATCH_MODE="${SSH_BATCH_MODE:-no}"
APP_DIR="${APP_DIR:-/opt/benchmarkAsset}"
SQLITE_PATH="${SQLITE_PATH:-/data/benchmarkAsset/app.db}"
IMAGES_DIR="${IMAGES_DIR:-/data/benchmarkAsset/images}"
FORCE="${FORCE:-1}"
RESTART_SERVICE="${RESTART_SERVICE:-1}"

SSH=(ssh -o BatchMode="$SSH_BATCH_MODE" "$REMOTE_USER@$REMOTE_HOST")
if [ -n "$SSH_KEY" ]; then
  SSH=(ssh -i "$SSH_KEY" -o BatchMode="$SSH_BATCH_MODE" "$REMOTE_USER@$REMOTE_HOST")
fi

"${SSH[@]}" \
  "APP_DIR='$APP_DIR' SQLITE_PATH='$SQLITE_PATH' IMAGES_DIR='$IMAGES_DIR' FORCE='$FORCE' RESTART_SERVICE='$RESTART_SERVICE' bash -s" <<'REMOTE'
set -euo pipefail

cd "$APP_DIR/backend"

if [ ! -f .env ]; then
  echo "Missing $APP_DIR/backend/.env. Run deploy/write-remote-env.sh first." >&2
  exit 1
fi
if [ ! -f "$SQLITE_PATH" ]; then
  echo "Missing SQLite database: $SQLITE_PATH" >&2
  exit 1
fi
if [ ! -d "$IMAGES_DIR" ]; then
  echo "Missing images directory: $IMAGES_DIR" >&2
  exit 1
fi

echo "Old SQLite:"
ls -lh "$SQLITE_PATH"
echo "Old image file count:"
find "$IMAGES_DIR" -maxdepth 1 -type f | wc -l

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
.venv/bin/pip install -q -r requirements.txt

.venv/bin/python migrate_schema.py

args=(--sqlite "$SQLITE_PATH" --images "$IMAGES_DIR")
if [ "$FORCE" = "1" ]; then
  args+=(--force)
fi
.venv/bin/python migrate_sqlite_to_neon_tos.py "${args[@]}"

if [ "$RESTART_SERVICE" = "1" ] && command -v systemctl >/dev/null 2>&1; then
  systemctl restart benchmark-asset
fi

echo "Health:"
curl -fsS http://127.0.0.1:8000/api/health || true
echo
REMOTE
