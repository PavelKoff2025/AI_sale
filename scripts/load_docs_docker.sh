#!/bin/bash
# Загрузка Markdown в RAG. Логика в образе backend: /app/scripts/load_md_to_chroma.py
# После обновления репозитория обязателен: docker compose build backend && docker compose up -d
# Запуск из корня репозитория: ./scripts/load_docs_docker.sh

set -e

echo "Загружаю документы в RAG (образ backend, load_md_to_chroma.py)..."

docker compose exec backend python /app/scripts/load_md_to_chroma.py
