#!/usr/bin/env bash
# Синхронизация проекта на VPS и пересборка контейнеров + загрузка RAG.
# Использование (с Mac):
#   export VPS_HOST=root@YOUR_VPS_IP
#   ./scripts/sync_vps.sh
#
# Не копирует: .env, chroma_data, node_modules (создайте .env на сервере вручную).

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ -z "${VPS_HOST:-}" ]; then
  echo "Задайте хост: VPS_HOST=root@IP ./scripts/sync_vps.sh"
  exit 1
fi
HOST="$VPS_HOST"
DEST="${VPS_DEST:-${HOST}:~/AI_sale/}"

echo "==> rsync -> ${DEST}"
rsync -avz \
  --exclude '.git' \
  --exclude 'node_modules' \
  --exclude 'frontend/node_modules' \
  --exclude 'chroma_data' \
  --exclude '.env' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '.DS_Store' \
  ./ "${DEST}"

echo "==> docker compose build & up on ${HOST}"
ssh "${HOST}" 'bash -s' <<'REMOTE'
set -euo pipefail
cd ~/AI_sale
chmod +x deploy.sh scripts/load_docs_docker.sh 2>/dev/null || true
docker compose build
docker compose up -d
echo "Waiting for backend..."
for i in $(seq 1 24); do
  if docker compose exec -T backend curl -sf http://localhost:8080/api/health >/dev/null 2>&1; then
    echo "Backend is up."
    break
  fi
  sleep 5
done
echo "WARNING: backend healthcheck not ready; continuing with load_docs anyway."
REMOTE

echo "==> load_docs_docker (docs/ + parsing_agent/data/raw)"
ssh "${HOST}" 'cd ~/AI_sale && ./scripts/load_docs_docker.sh'

echo "==> Done. Widget: http://'"${HOST#*@}"'/"
