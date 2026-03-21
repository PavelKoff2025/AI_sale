# AI Sale Agent

Автономный AI-агент продаж на базе ChatGPT с RAG (Retrieval-Augmented Generation).

## Компоненты

| Компонент | Технологии | Описание |
|-----------|-----------|----------|
| **Backend** | FastAPI, OpenAI, ChromaDB | API сервер с RAG и системным промптом |
| **Frontend** | React, TypeScript, Vite | Встраиваемый чат-виджет |
| **Parsing Agent** | Python, BeautifulSoup | Парсинг данных для RAG базы |

## Быстрый старт

### 1. Клонирование и настройка

```bash
cd AI_sale
cp .env.example .env
# Заполните OPENAI_API_KEY в .env
```

### 2. Запуск через Docker Compose

```bash
docker-compose up --build
```

### 3. Или запуск по отдельности

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**Загрузка данных в RAG:**
```bash
cd parsing_agent
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# Отредактируйте configs/sources.yaml с URL вашего сайта
python -m app.main --config configs/sources.yaml
```

## Архитектура

```
Пользователь → Widget (React) → Backend (FastAPI) → RAG (ChromaDB) + OpenAI GPT-4o
                                                      ↑
                                        Parsing Agent (данные)
```

## Документация

- [Архитектура проекта](docs/ARCHITECTURE.md)
- [Backend API](docs/BACKEND.md)
- [Frontend Widget](docs/FRONTEND.md)
- [Parsing Agent](docs/PARSING_AGENT.md)

## Endpoints

| Метод | URL | Описание |
|-------|-----|----------|
| POST | `/api/chat` | Отправка сообщения |
| POST | `/api/chat/stream` | Streaming ответ (SSE) |
| WS | `/ws/chat` | WebSocket чат |
| GET | `/api/health` | Проверка состояния |
| GET | `/api/knowledge` | Статистика RAG базы |
