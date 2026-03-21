# Деплой AI Sale Agent на VPS

## Требования к серверу

- **ОС:** Ubuntu 20.04+ / Debian 11+
- **RAM:** минимум 2 ГБ (рекомендуется 4 ГБ)
- **CPU:** 2 ядра
- **Диск:** 20 ГБ свободного места
- **Порты:** 80 (HTTP), 22 (SSH)

## Быстрый деплой (5 минут)

### 1. Скопировать проект на VPS

```bash
# С вашего компьютера:
scp -r ~/Desktop/AI_sale user@YOUR_VPS_IP:~/
```

### 2. Подключиться к VPS

```bash
ssh user@YOUR_VPS_IP
```

### 3. Проверить .env

```bash
cd ~/AI_sale
nano .env   # убедитесь что ключи заполнены
```

Обязательные ключи:
- `OPENAI_API_KEY` или `GIGACHAT_CREDENTIALS` (хотя бы один)
- `TELEGRAM_BOT_TOKEN` и `TELEGRAM_CHAT_ID` (для заявок)

### 4. Запустить деплой

```bash
chmod +x deploy.sh
./deploy.sh
```

Скрипт автоматически:
- Установит Docker (если нет)
- Соберёт все контейнеры
- Запустит сервисы
- Покажет статус

### 5. Загрузить базу знаний

```bash
chmod +x scripts/load_docs_docker.sh
./scripts/load_docs_docker.sh
```

### 6. Проверить

Откройте в браузере: `http://YOUR_VPS_IP`

## Архитектура на сервере

```
Nginx (порт 80)
  ├── /           → Frontend (React)
  ├── /api/       → Backend (FastAPI)
  └── /ws/        → WebSocket
          ↓
       Backend
          ↓
       ChromaDB (RAG)
```

Все сервисы работают в Docker-контейнерах. Внешний доступ только через порт 80.

## Управление

```bash
# Статус
docker compose ps

# Логи всех сервисов
docker compose logs -f

# Логи конкретного сервиса
docker compose logs -f backend

# Перезапуск
docker compose restart

# Остановка
docker compose down

# Обновление (после git pull)
docker compose build --no-cache && docker compose up -d
```

## Обновление базы знаний

Добавьте файлы в папку `docs/` и запустите:

```bash
./scripts/load_docs_docker.sh
```

## Привязка домена (опционально)

1. Направьте A-запись домена на IP вашего VPS
2. Установите Certbot для SSL:

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.ru
```

## Решение проблем

**Контейнеры не запускаются:**
```bash
docker compose logs
```

**Backend не отвечает:**
```bash
docker compose logs backend
# Проверить .env — есть ли ключи API
```

**Нет доступа по IP:**
```bash
# Проверить firewall
sudo ufw allow 80
sudo ufw allow 443
```

**Мало памяти:**
```bash
free -h
# Создать swap если < 2 ГБ RAM:
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```
