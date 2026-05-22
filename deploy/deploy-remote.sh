#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

REMOTE_HOST="${REMOTE_HOST:-115.190.185.17}"
REMOTE_USER="${REMOTE_USER:-root}"
SSH_KEY="${SSH_KEY:-}"
DOMAIN="${DOMAIN:-benchmark.jy-video.cn}"
APP_DIR="${APP_DIR:-/opt/benchmarkAsset}"
DATA_DIR="${DATA_DIR:-/data/benchmarkAsset}"
SYNC_DATA="${SYNC_DATA:-1}"
LETSENCRYPT_EMAIL="${LETSENCRYPT_EMAIL:-admin@jy-video.cn}"
BASIC_AUTH_USER="${BASIC_AUTH_USER:-benchmark}"
BASIC_AUTH_PASSWORD="${BASIC_AUTH_PASSWORD:-benchmark}"
BASIC_AUTH_OVERWRITE="${BASIC_AUTH_OVERWRITE:-0}"

SSH=(ssh -o BatchMode=yes "$REMOTE_USER@$REMOTE_HOST")
RSYNC_SSH=(ssh -o BatchMode=yes)
if [ -n "$SSH_KEY" ]; then
  SSH=(ssh -i "$SSH_KEY" -o BatchMode=yes "$REMOTE_USER@$REMOTE_HOST")
  RSYNC_SSH=(ssh -i "$SSH_KEY" -o BatchMode=yes)
fi
RSYNC_RSH="${RSYNC_SSH[*]}"

cd "$ROOT_DIR"

echo "Building frontend..."
npm --prefix frontend install
npm --prefix frontend run build
backend/.venv/bin/python -m py_compile backend/main.py backend/db.py backend/ai.py 2>/dev/null || true

echo "Preparing remote directories..."
"${SSH[@]}" "mkdir -p '$APP_DIR' '$DATA_DIR' /var/www/certbot"

echo "Syncing application code..."
rsync -az --delete \
  -e "$RSYNC_RSH" \
  --exclude 'backend/.venv/' \
  --exclude 'backend/data/' \
  --exclude 'frontend/node_modules/' \
  --exclude 'frontend/dev.log' \
  --exclude 'frontend/install.log' \
  --exclude '.DS_Store' \
  "$ROOT_DIR"/ "$REMOTE_USER@$REMOTE_HOST:$APP_DIR/"

if [ "$SYNC_DATA" = "1" ]; then
  echo "Syncing SQLite database and image data to $DATA_DIR..."
  rsync -az --delete -e "$RSYNC_RSH" "$ROOT_DIR/backend/data/" "$REMOTE_USER@$REMOTE_HOST:$DATA_DIR/"
else
  echo "Skipping data sync because SYNC_DATA=$SYNC_DATA"
fi

echo "Installing/updating remote runtime and service..."
"${SSH[@]}" "DOMAIN='$DOMAIN' APP_DIR='$APP_DIR' DATA_DIR='$DATA_DIR' LETSENCRYPT_EMAIL='$LETSENCRYPT_EMAIL' BASIC_AUTH_USER='$BASIC_AUTH_USER' BASIC_AUTH_PASSWORD='$BASIC_AUTH_PASSWORD' BASIC_AUTH_OVERWRITE='$BASIC_AUTH_OVERWRITE' bash -s" <<'REMOTE'
set -euo pipefail

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y python3.12-venv python3-pip nginx certbot python3-certbot-nginx apache2-utils ufw

mkdir -p "$DATA_DIR" /var/www/certbot
chmod 755 /data "$DATA_DIR" /var/www/certbot

cd "$APP_DIR"
if [ ! -d backend/.venv ]; then
  python3 -m venv backend/.venv
fi
backend/.venv/bin/pip install -r backend/requirements.txt
chmod +x deploy.sh start-production.sh

if [ ! -f /etc/nginx/.benchmark-asset.htpasswd ] || [ "${BASIC_AUTH_OVERWRITE:-0}" = "1" ]; then
  htpasswd -bc /etc/nginx/.benchmark-asset.htpasswd "$BASIC_AUTH_USER" "$BASIC_AUTH_PASSWORD"
  chmod 640 /etc/nginx/.benchmark-asset.htpasswd
  chown root:www-data /etc/nginx/.benchmark-asset.htpasswd
fi

cp deploy/benchmark-asset.service /etc/systemd/system/benchmark-asset.service
systemctl daemon-reload
systemctl enable benchmark-asset
systemctl restart benchmark-asset

rm -f /etc/nginx/sites-enabled/default
cp deploy/nginx-benchmark-asset.http.conf /etc/nginx/conf.d/benchmark-asset.conf
nginx -t
systemctl enable nginx
systemctl restart nginx

if [ ! -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
  certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "$LETSENCRYPT_EMAIL" --redirect
fi

cp deploy/nginx-benchmark-asset.conf /etc/nginx/conf.d/benchmark-asset.conf
nginx -t
systemctl reload nginx

ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

systemctl is-active benchmark-asset
systemctl is-active nginx
curl -fsS "http://127.0.0.1:8000/api/health"
echo
REMOTE

echo "Verifying public HTTPS..."
curl -fsS -u "$BASIC_AUTH_USER:$BASIC_AUTH_PASSWORD" "https://$DOMAIN/api/health"
echo
echo "Done: https://$DOMAIN/"
