# Тимлид — Главные правила проекта

## Иерархия агентов

```
ТИМЛИД
├── Агент Backend  — API, RAG, LLM, сессии
├── Агент Frontend — React виджет, UI/UX
└── Агент Парсер   — парсинг gkproject.ru
```

Все агенты подчиняются Тимлиду. Тимлид определяет:
- Архитектуру и стандарты кода
- Форматы данных между агентами
- Порядок разработки и приоритеты

## Проект: AI-агент продаж для ГК Проект (gkproject.ru)

**Клиент**: ООО «ГК Проект» — инженерные системы (котельные, отопление, водоснабжение, электрика, канализация)
**Телефон**: +7 495 908-74-74
**Сайт**: gkproject.ru

## Компоненты

| Компонент | Стек | Порт | Роль |
|-----------|------|------|------|
| Backend | FastAPI + OpenAI + ChromaDB | 8080 | API + RAG + LLM |
| Frontend | React + TypeScript + Vite | 3000 | Чат-виджет |
| Parsing Agent | Python + BeautifulSoup | — | Парсинг → RAG |
| ChromaDB | Векторная БД | 8000 | Хранение embeddings |

## Контракты между агентами

### Frontend → Backend

```
POST /api/chat         {message, session_id} → {message, sources, intent}
POST /api/chat/stream  {message, session_id} → SSE chunks
POST /api/leads/       {name, phone, message} → {status, lead_id}
WS   /ws/chat          JSON frames
```

### Parsing Agent → ChromaDB → Backend

```
Парсер: gkproject.ru → chunks + embeddings → ChromaDB
Backend: query → embedding → ChromaDB search → top-K → контекст для LLM
```

## Документация

| Документ | Описание |
|----------|----------|
| `docs/SCRIPT.md` | **Скрипт общения AI-агента** — основной системный промпт |
| `docs/ARCHITECTURE.md` | Общая архитектура проекта |
| `docs/AGENT_TEAMLEAD.md` | Тимлид — этот файл |
| `docs/AGENT_BACKEND.md` | Агент Backend |
| `docs/AGENT_FRONTEND.md` | Агент Frontend |
| `docs/AGENT_PARSER.md` | Агент Парсер (gkproject.ru) |
| `docs/BACKEND.md` | Техническая документация бэкенда |
| `docs/FRONTEND.md` | Техническая документация фронтенда |
| `docs/PARSING_AGENT.md` | Техническая документация парсера |

## Правила для всех агентов

1. Переменные окружения — только через `.env`, шаблон `.env.example`
2. `OPENAI_API_KEY` обязателен
3. Не коммитить: .env, data/raw/, node_modules/, __pycache__/
4. Формат коммитов: `feat:`, `fix:`, `docs:`, `refactor:`
5. Каждый агент работает автономно, но следует контрактам Тимлида

## Запуск

```bash
docker-compose up --build          # Всё сразу
cd backend && uvicorn app.main:app --reload --port 8080
cd frontend && npm run dev
cd parsing_agent && python -m app.main
```
