# Frontend — AI Sale Chat Widget

Встраиваемый чат-виджет на React + TypeScript. Плавающая кнопка в правом
нижнем углу, открывающая окно чата с AI-агентом. Streaming ответов через SSE.

---

## Содержимое

```
frontend/
├── index.html                       # HTML точка входа для Vite
├── package.json                     # npm зависимости и скрипты
├── tsconfig.json                    # TypeScript конфигурация (strict mode)
├── vite.config.ts                   # Vite — dev-сервер порт 3000, proxy на backend
├── tailwind.config.js               # TailwindCSS — кастомные цвета (primary)
├── postcss.config.js                # PostCSS для TailwindCSS
├── Dockerfile                       # Docker образ (node build → nginx)
│
└── src/
    ├── main.tsx                     # React entry — рендерит <App/> в #root
    ├── App.tsx                      # Корневой компонент — демо-страница + ChatWidget
    │
    ├── components/                  # UI компоненты
    │   ├── ChatWidget.tsx           # Корневой виджет — управляет open/close
    │   ├── ChatBubble.tsx           # Плавающая кнопка-пузырёк (иконка чата ↔ крестик)
    │   ├── ChatWindow.tsx           # Окно чата — собирает Header + MessageList + InputBar
    │   ├── Header.tsx               # Заголовок окна — название + кнопка закрытия
    │   ├── MessageList.tsx          # Скроллируемый список сообщений + auto-scroll
    │   ├── MessageItem.tsx          # Одно сообщение (user = синий справа, bot = серый слева)
    │   ├── InputBar.tsx             # Поле ввода + кнопка отправки (Enter для отправки)
    │   └── TypingIndicator.tsx      # Анимация "печатает..." (3 прыгающие точки)
    │
    ├── hooks/                       # React хуки
    │   ├── useChat.ts               # Логика чата — отправка, streaming, ошибки
    │   └── useSession.ts            # Управление session_id через localStorage
    │
    ├── styles/
    │   └── globals.css              # @tailwind base/components/utilities
    │
    └── utils/                       # Утилиты
        ├── api.ts                   # HTTP клиент — sendMessage() и streamMessage()
        ├── config.ts                # Конфигурация виджета (URL, тексты, цвета)
        └── types.ts                 # TypeScript интерфейсы
```

---

## Что делает каждый файл

### Компоненты

#### `ChatWidget.tsx` — Корневой виджет

- Управляет состоянием `isOpen` (открыт/закрыт)
- Рендерит `ChatBubble` (всегда) и `ChatWindow` (когда открыт)
- Позиция: `fixed bottom-6 right-6 z-[9999]`

#### `ChatBubble.tsx` — Плавающая кнопка

- Круглая кнопка 56x56px (`w-14 h-14`)
- Две иконки: чат (закрыто) ↔ крестик (открыто)
- Hover эффект: масштабирование + смена цвета
- ARIA label для accessibility

#### `ChatWindow.tsx` — Окно чата

- Размер: `380x520px` на десктопе, полноэкранный на мобильных
- Собирает три секции: `Header` + `MessageList` + `InputBar`
- Подключает хук `useChat()` для управления сообщениями
- Показывает приветственное сообщение если история пуста

#### `Header.tsx` — Заголовок

- Название из конфига (`"AI Помощник"`)
- Подзаголовок (`"Онлайн"`)
- Кнопка закрытия (крестик)
- Фон: `bg-primary-600` (индиго)

#### `MessageList.tsx` — Список сообщений

- Скроллируемый контейнер (`overflow-y-auto`)
- Авто-скролл вниз при новых сообщениях (`scrollIntoView`)
- Рендерит `MessageItem` для каждого сообщения

#### `MessageItem.tsx` — Сообщение

- **User**: синий фон, выравнивание справа, скруглённый без правого нижнего угла
- **Assistant**: серый фон, выравнивание слева, скруглённый без левого нижнего угла
- Показывает `TypingIndicator` если streaming и контент пуст

#### `InputBar.tsx` — Поле ввода

- Text input + кнопка отправки (стрелка)
- Enter для отправки, Shift+Enter не отправляет
- Заблокировано во время загрузки (`isLoading`)
- Placeholder из конфига

#### `TypingIndicator.tsx` — Анимация печати

- Три точки с `animate-bounce` и разными `animation-delay`
- Показывается пока streaming не начал возвращать контент

---

### Хуки

#### `useChat.ts` — Логика чата

Центральный хук, управляет всем чатом:

```
sendMessage(text) →
  1. Добавить user message в список
  2. Создать пустой assistant message (isStreaming: true)
  3. Вызвать streamMessage() из api.ts
  4. По мере получения чанков — обновлять content ассистента
  5. По завершении — isStreaming: false
  6. При ошибке — показать "Произошла ошибка"
```

**Возвращает**: `{ messages, isLoading, error, sendMessage, clearHistory }`

#### `useSession.ts` — Сессия

- Создаёт `session_id` (UUID v4) при первом визите
- Сохраняет в `localStorage` под ключом `ai_sale_session_id`
- `resetSession()` — создаёт новый ID и перезагружает страницу

---

### Утилиты

#### `api.ts` — API клиент

Две функции:

| Функция | Метод | Endpoint | Описание |
|---------|-------|----------|----------|
| `sendMessage()` | POST | `/api/chat` | Обычный запрос → ChatResponse |
| `streamMessage()` | POST | `/api/chat/stream` | SSE streaming → AsyncGenerator<string> |

`streamMessage()` — читает SSE поток:
- Каждая строка `data: {...}` парсится как JSON
- Если `type === "chunk"` → yield `content`
- Если `data: [DONE]` → остановка

#### `config.ts` — Конфигурация виджета

| Параметр | По умолчанию | Описание |
|----------|-------------|----------|
| `apiUrl` | `http://localhost:8080` | URL бэкенда (из `VITE_API_URL`) |
| `wsUrl` | `ws://localhost:8080/ws/chat` | WebSocket URL |
| `title` | `"AI Помощник"` | Заголовок виджета |
| `subtitle` | `"Онлайн"` | Подзаголовок |
| `primaryColor` | `#4F46E5` | Основной цвет |
| `position` | `bottom-right` | Позиция виджета |
| `greeting` | `"Здравствуйте! Чем могу помочь?"` | Приветствие |
| `placeholder` | `"Введите сообщение..."` | Placeholder поля ввода |

#### `types.ts` — TypeScript типы

| Интерфейс | Поля | Использование |
|-----------|------|---------------|
| `Message` | id, role, content, timestamp, sources?, isStreaming? | Одно сообщение в чате |
| `Source` | title, chunk_id, score | Источник из RAG |
| `ChatRequest` | message, session_id, metadata? | Запрос к API |
| `ChatResponse` | session_id, message, sources, intent, tokens_used | Ответ от API |
| `WidgetConfig` | apiUrl, wsUrl, title, subtitle, primaryColor, ... | Конфигурация |

---

## Сборка

```
vite.config.ts — dev сервер на порте 3000
├── proxy /api → http://localhost:8080 (бэкенд)
└── proxy /ws  → ws://localhost:8080   (WebSocket)
```

## Запуск

```bash
cd frontend
npm install
npm run dev        # → http://localhost:3000
```

## Скрипты

| Команда | Описание |
|---------|----------|
| `npm run dev` | Dev-сервер с hot reload |
| `npm run build` | Production сборка |
| `npm run build:widget` | Сборка standalone виджета |
| `npm run preview` | Preview production build |
| `npm run lint` | ESLint проверка |
| `npm run type-check` | TypeScript проверка типов |
