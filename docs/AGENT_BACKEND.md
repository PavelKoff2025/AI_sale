# Агент Backend — подчинён Тимлиду

## Роль

Обрабатывает запросы от Frontend виджета: классифицирует intent,
ищет контекст в RAG (ChromaDB), генерирует ответ через OpenAI GPT-4o,
управляет сессиями, принимает заявки (leads).

## Стек

Python 3.11+, FastAPI, OpenAI SDK, ChromaDB, Pydantic 2

## Структура модуля

```
backend/app/
├── main.py                    # FastAPI app + lifespan + middleware
├── api/
│   ├── router.py              # Главный роутер (chat, health, knowledge, leads, analytics)
│   ├── chat.py                # POST /api/chat, POST /api/chat/stream, WS /ws/chat
│   ├── health.py              # GET /api/health
│   ├── knowledge.py           # GET/DELETE /api/knowledge
│   ├── leads.py               # POST/GET /api/leads
│   └── analytics.py           # GET /api/analytics
├── core/
│   ├── config.py              # Settings из .env (Pydantic Settings)
│   ├── middleware.py           # RequestLoggingMiddleware (X-Request-ID)
│   └── dependencies.py        # DI
├── services/
│   ├── agent_service.py       # AgentService — мозг: intent → RAG → GPT → ответ
│   ├── session_service.py     # SessionService — in-memory история (sliding window 20 msg)
│   ├── intent_service.py      # classify_intent() — эвристика по ключевым словам
│   └── telegram_service.py    # TelegramService — уведомления о заявках в ТГ
├── models/
│   ├── chat.py                # ChatRequest, ChatResponse, Source
│   └── lead.py                # LeadRequest, LeadResponse
├── rag/
│   └── engine.py              # RAGEngine — embedding + ChromaDB search + фильтр по score
└── prompts/
    └── system.py              # Системный промпт ГК Проект
```

## Pipeline обработки сообщения

```
1. Запрос от Frontend (message + session_id)
2. intent_service.classify_intent(message) → services/pricing/contacts/lead/...
3. session_service.get_history(session_id) → последние 20 сообщений
4. rag_engine.search(message, top_k=5) → релевантные чанки (score >= 0.7)
5. build_system_prompt(company, rag_context) → системный промпт ГК Проект
6. OpenAI API (gpt-4o, temperature=0.7, max_tokens=1000)
7. session_service.add_message() → сохранить в историю
8. Ответ → Frontend (message + sources + intent + tokens_used)
```

## API Endpoints

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/chat` | Обычный запрос → JSON ответ |
| POST | `/api/chat/stream` | SSE streaming (чанк за чанком) |
| WS | `/ws/chat` | WebSocket real-time чат |
| GET | `/api/health` | Healthcheck |
| GET | `/api/knowledge/` | Статистика RAG базы |
| DELETE | `/api/knowledge/{id}` | Удалить чанк |
| POST | `/api/leads/` | Создать заявку (лид) → уведомление в Telegram |
| GET | `/api/leads/` | Список заявок |
| POST | `/api/leads/test-telegram` | Тестовое сообщение в Telegram |
| GET | `/api/analytics/` | Статистика сессий + RAG |

## Intent классификация

8 категорий: `services`, `pricing`, `process`, `guarantee`, `portfolio`, `reviews`, `contacts`, `lead`.

Эвристика по ключевым словам в `intent_service.py` — быстрая, без вызова LLM.

| Intent | Примеры ключевых слов |
|--------|----------------------|
| services | монтаж, котельн, отоплен, водоснабж, электри, канализац, тёплый пол |
| pricing | цен, стоимост, сколько стоит, бюджет, смет, расчёт |
| process | как работает, этап, процесс, сроки |
| guarantee | гарант, качеств, страхов |
| portfolio | работ, объект, кейс, проект, фото |
| reviews | отзыв, рекоменд |
| contacts | телефон, контакт, адрес, позвонить |
| lead | заявк, заказ, вызвать, записаться, консультац |

## Middleware

**RequestLoggingMiddleware** (`core/middleware.py`):
- Логирует каждый запрос: метод, путь, статус, время ответа в мс
- Добавляет заголовок `X-Request-ID` (UUID[:8])

## Сессии

- In-memory хранение (для dev; Redis для prod)
- Sliding window: последние 20 сообщений в контексте
- TTL: 30 минут без активности → автоочистка

## RAG Engine

- Embedding: OpenAI `text-embedding-3-small`
- Поиск: ChromaDB cosine similarity
- Top-K: 5 результатов, порог score >= 0.7
- Fallback: EphemeralClient если ChromaDB сервер недоступен

## Системный промпт

Роль: AI-ассистент ГК Проект. Отвечает ТОЛЬКО на основе RAG-контекста.
Направляет к конверсии. Не выдумывает цены и характеристики.
Классифицирует запрос по 7 категориям.

## Telegram-уведомления

При создании заявки (POST `/api/leads/`) бот отправляет уведомление в Telegram-чат.

**Настройка:**
1. Создать бота через @BotFather → `/newbot` → скопировать токен
2. Отправить боту любое сообщение
3. Получить `chat_id`: `https://api.telegram.org/bot<TOKEN>/getUpdates`
4. Для группового чата: добавить бота в группу (chat_id будет отрицательным)
5. Прописать в `.env`:
   ```
   TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
   TELEGRAM_CHAT_ID=987654321
   ```

**Архитектура:**
- `telegram_service.py` → async отправка через httpx + Telegram Bot API
- Уведомление отправляется в `BackgroundTasks` (не блокирует ответ клиенту)
- При отсутствии токена сервис gracefully отключается (warning в лог)
- Формат сообщения: имя, телефон, сообщение, источник, время, ID заявки
- Эндпоинт `/api/leads/test-telegram` — проверка работоспособности бота

## Правила кода

- Async everywhere: все I/O через async/await
- Типизация: все функции с type hints
- Конфиг: Pydantic Settings, всё из .env
- Ошибки: HTTPException с корректными status codes
- Логирование: `logging`, не print()
- Промпты: ТОЛЬКО в `app/prompts/` — не хардкодить
- Pydantic модели: обязательны для всех request/response
- Новый endpoint → обновить router.py
