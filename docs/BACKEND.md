# Backend Agent — Техническая документация

## 1. Назначение

Backend — центральный компонент системы. Принимает запросы от виджета,
маршрутизирует через системный промпт, обращается к RAG базе за контекстом
и генерирует ответы через OpenAI API.

## 2. Стек технологий

| Технология    | Версия   | Назначение                         |
|---------------|----------|------------------------------------|
| Python        | 3.11+    | Язык                               |
| FastAPI       | 0.115+   | Web-фреймворк                      |
| Uvicorn       | 0.34+    | ASGI сервер                        |
| LangChain     | 0.3+     | Оркестрация LLM + RAG              |
| OpenAI SDK    | 1.60+    | Взаимодействие с GPT               |
| ChromaDB      | 0.5+     | Локальная векторная БД             |
| Pydantic      | 2.0+     | Валидация данных                   |
| Redis         | —        | Кэш сессий (опционально)          |

## 3. Структура модуля

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # Точка входа FastAPI
│   ├── api/
│   │   ├── __init__.py
│   │   ├── router.py           # Главный роутер
│   │   ├── chat.py             # POST /api/chat, WebSocket /ws/chat
│   │   ├── health.py           # GET /api/health
│   │   └── knowledge.py        # CRUD для базы знаний (админ)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py           # Настройки из .env (Pydantic Settings)
│   │   ├── dependencies.py     # DI для сервисов
│   │   └── middleware.py       # CORS, rate limiting, logging
│   ├── services/
│   │   ├── __init__.py
│   │   ├── agent_service.py    # Главная логика агента
│   │   ├── chat_service.py     # Управление диалогом
│   │   └── session_service.py  # Хранение истории сессий
│   ├── models/
│   │   ├── __init__.py
│   │   ├── chat.py             # ChatRequest, ChatResponse
│   │   ├── knowledge.py        # KnowledgeChunk
│   │   └── session.py          # SessionState
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── engine.py           # RAGEngine — поиск по базе знаний
│   │   ├── embeddings.py       # Создание embeddings
│   │   └── retriever.py        # ChromaDB retriever
│   └── prompts/
│       ├── __init__.py
│       ├── system.py           # Системные промпты
│       ├── router_prompt.py    # Промпт классификации
│       └── templates.py        # Шаблоны ответов
├── tests/
│   ├── test_chat.py
│   ├── test_rag.py
│   └── conftest.py
├── scripts/
│   └── seed_knowledge.py       # Скрипт начальной загрузки данных
├── requirements.txt
├── Dockerfile
└── README.md
```

## 4. API Endpoints

### 4.1 REST API

| Метод  | Путь               | Описание                    |
|--------|--------------------|-----------------------------|
| POST   | `/api/chat`        | Отправка сообщения агенту   |
| GET    | `/api/health`      | Проверка состояния сервиса  |
| POST   | `/api/knowledge`   | Добавление знаний (админ)   |
| GET    | `/api/knowledge`   | Список загруженных чанков   |
| DELETE | `/api/knowledge/{id}` | Удаление чанка           |

### 4.2 WebSocket

| Путь            | Описание                          |
|-----------------|-----------------------------------|
| `/ws/chat`      | Streaming чат с real-time ответами|

### 4.3 Формат запроса/ответа

**POST /api/chat**

Request:
```json
{
  "message": "Расскажите о ваших услугах",
  "session_id": "uuid-session-123",
  "metadata": {
    "page_url": "https://example.com/pricing",
    "user_agent": "Mozilla/5.0..."
  }
}
```

Response (streaming SSE):
```json
{
  "session_id": "uuid-session-123",
  "message": "Мы предлагаем следующие услуги...",
  "sources": [
    {"title": "Услуги компании", "chunk_id": "ch_001", "score": 0.92}
  ],
  "intent": "sales_inquiry",
  "tokens_used": 450
}
```

## 5. Системный промпт — архитектура

### 5.1 Многоуровневая маршрутизация

```python
SYSTEM_PROMPT = """
Ты — AI-ассистент по продажам компании {company_name}.

ПРАВИЛА ПОВЕДЕНИЯ:
1. Отвечай только на вопросы, связанные с продуктами и услугами компании.
2. Используй ТОЛЬКО информацию из предоставленного контекста (RAG).
3. Если информации нет в контексте — честно скажи и предложи связаться с менеджером.
4. Будь вежливым, профессиональным, лаконичным.
5. Направляй диалог к конверсии (покупка, заявка, звонок).

КЛАССИФИКАЦИЯ ЗАПРОСА:
- sales_inquiry: вопрос о товарах/услугах → ответь с RAG контекстом
- faq: частый вопрос → ответь с RAG контекстом
- support: проблема/жалоба → предложи связаться с поддержкой
- off_topic: не по теме → вежливо верни к теме

КОНТЕКСТ ИЗ БАЗЫ ЗНАНИЙ:
{rag_context}

ИСТОРИЯ ДИАЛОГА:
{chat_history}
"""
```

### 5.2 Логика agent_service

```python
class AgentService:
    async def process_message(self, message, session_id):
        # 1. Получить историю сессии
        history = await self.session_service.get_history(session_id)

        # 2. Поиск в RAG
        rag_results = await self.rag_engine.search(message, top_k=5)

        # 3. Формирование промпта
        prompt = self.build_prompt(
            message=message,
            rag_context=rag_results,
            history=history
        )

        # 4. Вызов OpenAI API
        response = await self.llm.agenerate(prompt)

        # 5. Сохранить в историю
        await self.session_service.add_message(session_id, message, response)

        return response
```

## 6. RAG Engine

### 6.1 Конфигурация

```python
RAG_CONFIG = {
    "embedding_model": "text-embedding-3-small",
    "chunk_size": 500,          # токенов
    "chunk_overlap": 50,        # перекрытие
    "top_k": 5,                 # количество результатов
    "score_threshold": 0.7,     # минимальный порог релевантности
    "collection_name": "ai_sale_knowledge"
}
```

### 6.2 Поиск

```
Query → Embedding → ChromaDB similarity search → Top-K chunks → Filter by score → Context
```

### 6.3 Метаданные чанков

Каждый чанк хранится с метаданными:
```json
{
  "id": "ch_001",
  "text": "Текст чанка...",
  "metadata": {
    "source": "website",
    "url": "https://example.com/services",
    "title": "Услуги компании",
    "category": "services",
    "created_at": "2025-01-15T10:00:00Z"
  },
  "embedding": [0.023, -0.015, ...]
}
```

## 7. Управление сессиями

- Сессия создаётся при первом сообщении (UUID v4)
- История хранится in-memory (dev) или Redis (prod)
- Максимум 20 сообщений в контексте (sliding window)
- TTL сессии: 30 минут без активности

## 8. Запуск

### Локально

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env  # заполнить OPENAI_API_KEY

# Запуск
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

### Docker

```bash
docker build -t ai-sale-backend .
docker run -p 8080:8080 --env-file ../.env ai-sale-backend
```

## 9. Тестирование

```bash
# Unit тесты
pytest tests/ -v

# Тест API
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Какие у вас услуги?", "session_id": "test-123"}'
```

## 10. Инструкции для AI-агента (Cursor)

При работе с Backend:
1. Всегда проверяй, что `OPENAI_API_KEY` установлен в `.env`
2. Для RAG используй ChromaDB — он запускается встроенно (без отдельного сервера в dev)
3. Streaming ответы — через SSE (Server-Sent Events) или WebSocket
4. Все промпты хранятся в `app/prompts/` — НЕ хардкодь в сервисах
5. Pydantic модели — обязательны для всех request/response
6. Async everywhere — все I/O операции должны быть асинхронными
7. При добавлении нового endpoint — добавляй тест в `tests/`
