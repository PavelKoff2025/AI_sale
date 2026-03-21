# Backend — AI Sale Agent API

FastAPI сервер с RAG и OpenAI GPT-4o. Принимает запросы от виджета,
ищет контекст в базе знаний, генерирует ответы через системный промпт.

---

## Содержимое

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                  # Точка входа FastAPI
│   │
│   ├── api/                     # HTTP и WebSocket endpoints
│   │   ├── __init__.py
│   │   ├── router.py            # Главный роутер — собирает все sub-routers
│   │   ├── chat.py              # POST /api/chat, POST /api/chat/stream (SSE), WS /ws/chat
│   │   ├── health.py            # GET /api/health — проверка состояния
│   │   └── knowledge.py         # GET/DELETE /api/knowledge — управление RAG базой
│   │
│   ├── core/                    # Конфигурация и инфраструктура
│   │   ├── __init__.py
│   │   ├── config.py            # Pydantic Settings — все настройки из .env
│   │   └── dependencies.py      # FastAPI Dependency Injection
│   │
│   ├── services/                # Бизнес-логика
│   │   ├── __init__.py
│   │   ├── agent_service.py     # AgentService — главный мозг: RAG → промпт → GPT → ответ
│   │   └── session_service.py   # SessionService — in-memory хранение истории диалогов
│   │
│   ├── models/                  # Pydantic модели данных
│   │   ├── __init__.py
│   │   └── chat.py              # ChatRequest, ChatResponse, Source
│   │
│   ├── rag/                     # RAG Engine — поиск по базе знаний
│   │   ├── __init__.py
│   │   └── engine.py            # RAGEngine — embedding запроса → ChromaDB поиск → top-K
│   │
│   └── prompts/                 # Системные промпты
│       ├── __init__.py
│       └── system.py            # SYSTEM_PROMPT_TEMPLATE + build_system_prompt()
│
├── tests/                       # Тесты
│   └── __init__.py
├── scripts/                     # Утилиты
├── requirements.txt             # Python зависимости
└── Dockerfile                   # Docker образ
```

---

## Что делает каждый файл

### `app/main.py` — Точка входа

- Создаёт FastAPI приложение
- Настраивает CORS middleware (разрешённые origins из .env)
- При старте (lifespan) инициализирует RAG engine — подключение к ChromaDB
- Подключает REST роутер (`/api/*`) и WebSocket (`/ws/chat`)

### `app/api/chat.py` — Чат endpoints

Три способа общения с агентом:

| Endpoint | Тип | Описание |
|----------|-----|----------|
| `POST /api/chat` | REST | Одноразовый запрос → полный ответ JSON |
| `POST /api/chat/stream` | SSE | Streaming — ответ приходит по чанкам через Server-Sent Events |
| `WS /ws/chat` | WebSocket | Real-time двусторонняя связь |

**Формат запроса:**
```json
{
  "message": "Какие у вас услуги?",
  "session_id": "uuid-123",
  "metadata": {"page_url": "..."}
}
```

**Формат ответа:**
```json
{
  "session_id": "uuid-123",
  "message": "Мы предлагаем...",
  "sources": [{"title": "Услуги", "chunk_id": "ch_001", "score": 0.92}],
  "intent": "general",
  "tokens_used": 450
}
```

### `app/api/health.py` — Healthcheck

- `GET /api/health` — возвращает `{"status": "healthy"}` для мониторинга

### `app/api/knowledge.py` — Управление базой знаний

- `GET /api/knowledge/` — статистика коллекции (количество документов)
- `DELETE /api/knowledge/{chunk_id}` — удаление конкретного чанка

### `app/core/config.py` — Конфигурация

Все настройки читаются из `.env` через Pydantic Settings:

| Переменная | По умолчанию | Описание |
|------------|-------------|----------|
| `OPENAI_API_KEY` | — | Ключ OpenAI API (обязателен) |
| `OPENAI_MODEL` | `gpt-4o` | Модель LLM |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | Модель для embeddings |
| `CHROMA_HOST` | `localhost` | Хост ChromaDB |
| `CHROMA_PORT` | `8000` | Порт ChromaDB |
| `CHROMA_COLLECTION` | `ai_sale_knowledge` | Имя коллекции |
| `BACKEND_PORT` | `8080` | Порт сервера |
| `CORS_ORIGINS` | `localhost:3000,5173` | Разрешённые origins |
| `COMPANY_NAME` | `Your Company` | Название компании для промпта |
| `RAG_TOP_K` | `5` | Кол-во результатов из RAG |
| `RAG_SCORE_THRESHOLD` | `0.7` | Минимальный порог релевантности |
| `SESSION_MAX_MESSAGES` | `20` | Макс. сообщений в контексте |
| `SESSION_TTL_SECONDS` | `1800` | Время жизни сессии (30 мин) |

### `app/services/agent_service.py` — Главная логика агента

Класс `AgentService` — центр обработки каждого сообщения:

```
1. Получить историю сессии (session_service)
2. Поиск в RAG базе (rag_engine.search → top-5 чанков)
3. Собрать системный промпт (company + RAG контекст + история)
4. Вызвать OpenAI API (gpt-4o, temperature=0.7, max_tokens=1000)
5. Сохранить в историю (user + assistant)
6. Вернуть ChatResponse с sources
```

Два режима:
- `process_message()` — обычный ответ (целиком)
- `process_message_stream()` — streaming (AsyncGenerator, чанк за чанком)

### `app/services/session_service.py` — Сессии

Класс `SessionService` — управление историей диалогов:

- **Хранение**: in-memory dict (для dev; заменить на Redis для prod)
- **Sliding window**: хранит все сообщения, но в контекст отдаёт последние 20
- **TTL**: автоматическая очистка сессий неактивных > 30 минут
- **Формат**: `[{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]`

### `app/rag/engine.py` — RAG Engine

Класс `RAGEngine` — поиск по базе знаний:

- **initialize()** — подключается к ChromaDB (HttpClient или EphemeralClient как fallback)
- **search(query, top_k)** — создаёт embedding запроса, ищет в ChromaDB, фильтрует по score >= 0.7
- **Формат результата**: `[{id, text, metadata, score}]`
- **get_collection_stats()** — кол-во документов в коллекции
- **delete_chunk(id)** — удаление чанка по ID

### `app/prompts/system.py` — Системный промпт

Шаблон `SYSTEM_PROMPT_TEMPLATE` с подстановкой:
- `{company_name}` — название компании
- `{rag_context}` — найденные чанки из RAG базы

Промпт определяет поведение:
- Отвечать ТОЛЬКО на основе контекста из RAG
- Не выдумывать цены и характеристики
- Классифицировать запрос (продажи / FAQ / поддержка / off-topic)
- Направлять к конверсии

### `app/models/chat.py` — Модели данных

| Модель | Поля | Назначение |
|--------|------|-----------|
| `ChatRequest` | message, session_id?, metadata? | Входящий запрос |
| `ChatResponse` | session_id, message, sources[], intent, tokens_used | Ответ агента |
| `Source` | title, chunk_id, score | Источник из RAG |

---

## Запуск

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
# Убедиться что OPENAI_API_KEY в ../.env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

## Тест

```bash
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Какие у вас услуги?"}'
```
