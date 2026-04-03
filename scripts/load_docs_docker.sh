#!/bin/bash
# Логика загрузки — в образе backend: /app/scripts/load_md_to_chroma.py
# На VPS без git: скопируйте этот файл с Mac в ~/AI_sale/scripts/, затем:
#   docker compose build backend && docker compose up -d
# Запуск из корня репозитория: ./scripts/load_docs_docker.sh

set -euo pipefail

LOADER="/app/scripts/load_md_to_chroma.py"
echo "=== RAG loader v3 (in-image) ==="

if ! docker compose exec -T backend test -f "$LOADER" 2>/dev/null; then
  echo ""
  echo "ОШИБКА: в контейнере backend нет $LOADER"
  echo "  1) Обновите файлы проекта на сервере (rsync/scp с Mac или git pull)."
  echo "  2) Пересоберите образ:  docker compose build backend && docker compose up -d"
  echo ""
  echo "Если видите HttpClient / python -c — у вас СТАРЫЙ scripts/load_docs_docker.sh на диске."
  echo "С Mac:  scp scripts/load_docs_docker.sh root@VPS:~/AI_sale/scripts/"
  exit 1
fi

docker compose exec backend python "$LOADER"
