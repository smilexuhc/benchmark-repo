#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

REMOTE_HOST="${REMOTE_HOST:-115.190.185.17}"
REMOTE_USER="${REMOTE_USER:-root}"
SSH_KEY="${SSH_KEY:-}"
DOMAIN="${DOMAIN:-benchmark.jy-video.cn}"
APP_DIR="${APP_DIR:-/opt/benchmarkAsset}"
DATA_DIR="${DATA_DIR:-/data/benchmarkAsset}"
LETSENCRYPT_EMAIL="${LETSENCRYPT_EMAIL:-admin@jy-video.cn}"
BASIC_AUTH_USER="${BASIC_AUTH_USER:-benchmark}"
BASIC_AUTH_PASSWORD="${BASIC_AUTH_PASSWORD:-benchmark}"
BASIC_AUTH_OVERWRITE="${BASIC_AUTH_OVERWRITE:-0}"
OPENROUTER_API_KEY="${OPENROUTER_API_KEY:-}"
OPENROUTER_BASE_URL="${OPENROUTER_BASE_URL:-https://proxy.offerin.cn/openrouter/api/v1}"
TEXT_MODEL="${TEXT_MODEL:-anthropic/claude-opus-4.7}"
IMAGE_MODEL="${IMAGE_MODEL:-openai/gpt-5.4-image-2}"
IMAGE_ASPECT_RATIO="${IMAGE_ASPECT_RATIO:-3:2}"
IMAGE_SIZE="${IMAGE_SIZE:-2K}"

required_env=(DATABASE_URL TOS_BUCKET TOS_REGION TOS_ENDPOINT TOS_ACCESS_KEY_ID TOS_SECRET_ACCESS_KEY)
for name in "${required_env[@]}"; do
  if [ -z "${!name:-}" ]; then
    echo "Missing required environment variable: $name" >&2
    exit 1
  fi
done

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

echo "Installing/updating remote runtime and service..."
"${SSH[@]}" "DOMAIN='$DOMAIN' APP_DIR='$APP_DIR' DATA_DIR='$DATA_DIR' LETSENCRYPT_EMAIL='$LETSENCRYPT_EMAIL' BASIC_AUTH_USER='$BASIC_AUTH_USER' BASIC_AUTH_PASSWORD='$BASIC_AUTH_PASSWORD' BASIC_AUTH_OVERWRITE='$BASIC_AUTH_OVERWRITE' DATABASE_URL='$DATABASE_URL' TOS_BUCKET='$TOS_BUCKET' TOS_REGION='$TOS_REGION' TOS_ENDPOINT='$TOS_ENDPOINT' TOS_ACCESS_KEY_ID='$TOS_ACCESS_KEY_ID' TOS_SECRET_ACCESS_KEY='$TOS_SECRET_ACCESS_KEY' OPENROUTER_API_KEY='$OPENROUTER_API_KEY' OPENROUTER_BASE_URL='$OPENROUTER_BASE_URL' TEXT_MODEL='$TEXT_MODEL' IMAGE_MODEL='$IMAGE_MODEL' IMAGE_ASPECT_RATIO='$IMAGE_ASPECT_RATIO' IMAGE_SIZE='$IMAGE_SIZE' bash -s" <<'REMOTE'
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

cat > backend/.env <<EOF
DATABASE_URL=$DATABASE_URL
TOS_BUCKET=$TOS_BUCKET
TOS_REGION=$TOS_REGION
TOS_ENDPOINT=$TOS_ENDPOINT
TOS_ACCESS_KEY_ID=$TOS_ACCESS_KEY_ID
TOS_SECRET_ACCESS_KEY=$TOS_SECRET_ACCESS_KEY
OPENROUTER_API_KEY=${OPENROUTER_API_KEY:-}
OPENROUTER_BASE_URL=${OPENROUTER_BASE_URL:-https://proxy.offerin.cn/openrouter/api/v1}
TEXT_MODEL=${TEXT_MODEL:-anthropic/claude-opus-4.7}
IMAGE_MODEL=${IMAGE_MODEL:-openai/gpt-5.4-image-2}
IMAGE_ASPECT_RATIO=${IMAGE_ASPECT_RATIO:-3:2}
IMAGE_SIZE=${IMAGE_SIZE:-2K}
EOF
chmod 600 backend/.env

cd backend
.venv/bin/python migrate_schema.py
cd ..

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
