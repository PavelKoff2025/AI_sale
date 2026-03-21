# AI Sale Agent — Архитектура проекта

## 1. Обзор

Автономный AI-агент продаж на базе ChatGPT с RAG (Retrieval-Augmented Generation).
Система состоит из трёх независимых компонентов, которые взаимодействуют через API.

## 2. Компоненты системы

```
┌─────────────────────────────────────────────────────────────────┐
│                        ПОЛЬЗОВАТЕЛЬ                             │
│                    (сайт клиента)                               │
└──────────────────────┬──────────────────────────────────────────┘
                       │  iframe / JS Widget
                       ▼
┌──────────────────────────────────────────┐
│           FRONTEND (Widget)              │
│  React + TypeScript                      │
│  - Чат-интерфейс                         │
│  - Встраиваемый виджет (iframe/script)   │
│  - WebSocket для real-time               │
└──────────────────────┬───────────────────┘
                       │  REST API / WebSocket
                       ▼
┌──────────────────────────────────────────┐
│           BACKEND (FastAPI)              │
│  Python 3.11+                            │
│                                          │
│  ┌────────────┐  ┌───────────────────┐   │
│  │  System    │  │   RAG Engine      │   │
│  │  Prompt    │──│  ChromaDB (local) │   │
│  │  Router    │  │  Pinecone (prod)  │   │
│  └────────────┘  └───────────────────┘   │
│         │                │               │
│         ▼                ▼               │
│  ┌─────────────────────────────────┐     │
│  │      OpenAI ChatGPT API        │     │
│  │  gpt-4o / gpt-4o-mini          │     │
│  └─────────────────────────────────┘     │
└──────────────────────────────────────────┘
                       ▲
                       │  Загрузка данных в RAG
┌──────────────────────┴───────────────────┐
│        PARSING AGENT                     │
│  Python 3.11+                            │
│  - Парсинг сайтов (BeautifulSoup)        │
│  - Обработка PDF/DOCX                   │
│  - Chunking + Embedding                 │
│  - Загрузка в векторную БД              │
└──────────────────────────────────────────┘
```

## 3. Технологический стек

| Компонент       | Технологии                                           |
|-----------------|------------------------------------------------------|
| **Backend**     | Python 3.11, FastAPI, LangChain, OpenAI API, Uvicorn |
| **RAG DB**      | ChromaDB (локально), Pinecone (продакшн)             |
| **Embeddings**  | OpenAI text-embedding-3-small                        |
| **LLM**         | GPT-4o (основной), GPT-4o-mini (фолбэк)             |
| **Frontend**    | React 18, TypeScript, Vite, TailwindCSS              |
| **Parsing**     | Python, BeautifulSoup4, PyPDF2, python-docx          |
| **Инфра**       | Docker, Docker Compose, Nginx                        |
| **Деплой**      | VPS / Railway / Render                               |

## 4. Структура проекта

```
AI_sale/
├── backend/                  # FastAPI бэкенд
│   ├── app/
│   │   ├── api/              # REST endpoints + WebSocket
│   │   ├── core/             # Конфиг, security, middleware
│   │   ├── services/         # Бизнес-логика (agent service)
│   │   ├── models/           # Pydantic модели
│   │   ├── rag/              # RAG engine (retrieval, embeddings)
│   │   └── prompts/          # Системные промпты
│   ├── tests/
│   ├── scripts/              # Утилиты (seed, migration)
│   ├── requirements.txt
│   ├── Dockerfile
│   └── README.md
├── frontend/                 # React виджет
│   ├── src/
│   │   ├── components/       # UI компоненты чата
│   │   ├── hooks/            # React хуки (useChat, useWebSocket)
│   │   ├── styles/           # TailwindCSS стили
│   │   └── utils/            # API клиент, helpers
│   ├── public/
│   ├── tests/
│   ├── package.json
│   ├── Dockerfile
│   └── README.md
├── parsing_agent/            # Агент парсинга данных
│   ├── app/
│   │   ├── parsers/          # Парсеры (web, pdf, docx)
│   │   ├── processors/       # Chunking, cleaning
│   │   └── loaders/          # Загрузка в векторную БД
│   ├── data/
│   │   ├── raw/              # Сырые данные
│   │   └── processed/        # Обработанные чанки
│   ├── configs/              # Конфиги источников
│   ├── tests/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── README.md
├── docker/                   # Docker конфиги
│   └── nginx.conf
├── docs/                     # Документация
│   ├── ARCHITECTURE.md       # ← этот файл
│   ├── BACKEND.md
│   ├── FRONTEND.md
│   └── PARSING_AGENT.md
├── docker-compose.yml
├── .env.example
└── README.md
```

## 5. Потоки данных

### 5.1 Пользовательский запрос (runtime)

```
1. Пользователь → Widget: отправляет сообщение
2. Widget → Backend API: POST /api/chat или WebSocket
3. Backend → System Prompt Router:
   a. Классифицирует тип вопроса (продажи, FAQ, off-topic)
   b. Определяет нужен ли контекст из RAG
4. Backend → RAG Engine:
   a. Создаёт embedding запроса
   b. Ищет top-K релевантных чанков в ChromaDB
5. Backend → OpenAI API:
   a. Формирует prompt = system_prompt + RAG контекст + история + вопрос
   b. Получает ответ от GPT-4o
6. Backend → Widget: возвращает ответ (streaming)
7. Widget → Пользователь: отображает ответ
```

### 5.2 Загрузка данных (parsing pipeline)

```
1. Parsing Agent: получает конфиг с URL/файлами
2. Parser: извлекает текст из источника
3. Processor: очищает, делит на чанки (500-1000 токенов)
4. Loader:
   a. Создаёт embeddings через OpenAI API
   b. Загружает в ChromaDB коллекцию
5. Backend: при следующем запросе видит новые данные
```

## 6. Системный промпт — логика маршрутизации

Backend использует многоуровневый системный промпт:

```
LEVEL 1: Классификация запроса
  → Продажи / FAQ / Поддержка / Off-topic

LEVEL 2: Решение о RAG
  → Нужен контекст из базы знаний? Да/Нет

LEVEL 3: Генерация ответа
  → Формирует ответ с учётом контекста и роли
```

## 7. Переменные окружения

```env
# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# RAG
CHROMA_HOST=localhost
CHROMA_PORT=8000
CHROMA_COLLECTION=ai_sale_knowledge

# Backend
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8080
CORS_ORIGINS=http://localhost:3000

# Frontend
VITE_API_URL=http://localhost:8080
VITE_WS_URL=ws://localhost:8080/ws
```

## 8. Локальная разработка

```bash
# 1. Клонируем и заходим
cd AI_sale

# 2. Копируем env
cp .env.example .env
# Заполняем OPENAI_API_KEY

# 3. Запускаем всё через Docker Compose
docker-compose up --build

# Или по отдельности:
# Backend
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload

# Frontend
cd frontend && npm install && npm run dev

# Parsing Agent
cd parsing_agent && pip install -r requirements.txt && python -m app.main
```

## 9. Деплой (Production)

1. **VPS**: Docker Compose + Nginx reverse proxy
2. **Railway/Render**: отдельные сервисы для backend + frontend
3. **ChromaDB → Pinecone**: миграция векторной БД в облако
4. **SSL**: Let's Encrypt через Nginx

## 10. Версионирование

- **v0.1** — MVP: чат-виджет + RAG + базовый парсинг
- **v0.2** — Streaming ответов, история диалогов
- **v0.3** — Аналитика, A/B тестирование промптов
- **v1.0** — Production-ready с мониторингом
