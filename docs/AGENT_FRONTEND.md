# Агент Frontend — подчинён Тимлиду

## Роль

Встраиваемый чат-виджет для сайта ГК Проект. Отправляет сообщения
Backend агенту, отображает streaming ответы, собирает заявки (leads),
предлагает быстрые ответы (quick replies).

## Стек

React 18, TypeScript 5, Vite 6, TailwindCSS 3

## Структура модуля

```
frontend/src/
├── main.tsx                         # React entry
├── App.tsx                          # Демо-страница ГК Проект + ChatWidget
├── components/
│   ├── ChatWidget.tsx               # Корневой: управляет open/close
│   ├── ChatBubble.tsx               # Плавающая кнопка (синяя)
│   ├── ChatWindow.tsx               # Окно чата: Header + Messages + QuickReplies + Input
│   ├── Header.tsx                   # Заголовок: "ГК Проект" + аватар + кнопка заявки + закрыть
│   ├── MessageList.tsx              # Список сообщений + auto-scroll
│   ├── MessageItem.tsx              # Сообщение: аватар "ГК" для бота, синий для юзера
│   ├── InputBar.tsx                 # Поле ввода + кнопка отправки
│   ├── TypingIndicator.tsx          # Анимация "печатает..." (3 прыгающие точки)
│   ├── QuickReplies.tsx             # 6 быстрых вопросов (при пустом чате)
│   └── LeadForm.tsx                 # Форма заявки: имя + телефон + комментарий
├── hooks/
│   ├── useChat.ts                   # Логика: отправка → SSE streaming → обновление
│   └── useSession.ts               # session_id в localStorage
├── styles/
│   └── globals.css                  # TailwindCSS base
└── utils/
    ├── api.ts                       # sendMessage() + streamMessage() (SSE)
    ├── config.ts                    # Конфиг: title="ГК Проект", greeting, placeholder
    └── types.ts                     # Message, Source, ChatRequest, ChatResponse, WidgetConfig
```

## Компоненты — что делает каждый

### ChatWidget (корневой)

Управляет состоянием open/close. Рендерит `ChatBubble` (всегда) и `ChatWindow` (когда открыт).
Позиция: `fixed bottom-6 right-6 z-[9999]`.

### ChatBubble

Круглая кнопка 56x56px. Иконка чата (закрыто) ↔ крестик (открыто).
Цвет: `blue-600`, hover: `blue-700` + scale 1.05.

### ChatWindow (центральный компонент)

- Размер: 380x520px на десктопе, fullscreen на мобильных (`max-sm:`)
- При пустом чате: приветственное сообщение + QuickReplies
- Определяет "заявк" / "заказ" в тексте → открывает LeadForm
- Кнопка заявки (телефон) в Header
- Собирает: Header + MessageList + QuickReplies + InputBar / LeadForm

### Header

- Аватар "ГК" (синий кружок) + название "ГК Проект" + "Онлайн-консультант"
- Кнопка заявки (иконка телефона) → открывает LeadForm
- Кнопка закрытия (крестик)

### MessageList

- Скроллируемый контейнер (`overflow-y-auto`)
- Авто-скролл вниз при новых сообщениях (`scrollIntoView`)

### MessageItem

- **User**: синий фон (`blue-600`), выравнивание справа
- **Assistant**: серый фон (`gray-100`), выравнивание слева, аватар "ГК"
- Показывает `TypingIndicator` при streaming без контента

### InputBar

- Text input + кнопка отправки (стрелка)
- Enter для отправки, Shift+Enter — нет
- Заблокировано при `isLoading`

### TypingIndicator

- 3 точки с `animate-bounce` и разными `animation-delay`

### QuickReplies

6 кнопок быстрых вопросов (видимы только при пустом чате):

1. "Какие услуги вы предоставляете?"
2. "Сколько стоит монтаж котельной?"
3. "Как вы работаете?"
4. "Какие гарантии?"
5. "Показать примеры работ"
6. "Контакты"

### LeadForm

Форма заявки с тремя полями:
- Имя (обязательно)
- Телефон (обязательно)
- Комментарий (необязательно)

Отправка: `POST /api/leads/` → Backend агент.
Статусы: idle → sending → sent (галочка) / error (показать телефон).

## Хуки

### useChat

Центральный хук чата:
1. Добавляет user message + пустой assistant message (`isStreaming: true`)
2. Вызывает `streamMessage()` из `api.ts`
3. По мере получения SSE чанков — обновляет content ассистента
4. По завершении — `isStreaming: false`
5. При ошибке — "Произошла ошибка. Попробуйте позже."

Возвращает: `{ messages, isLoading, error, sendMessage, clearHistory }`

### useSession

- Создаёт `session_id` (UUID) при первом визите
- Хранит в `localStorage` под ключом `ai_sale_session_id`
- `resetSession()` — новый ID + перезагрузка

## Связь с Backend Agent

| Действие | Endpoint | Метод |
|----------|----------|-------|
| Отправить сообщение | `/api/chat/stream` | POST (SSE) |
| Отправить заявку | `/api/leads/` | POST |
| WebSocket чат | `/ws/chat` | WS |

## Конфигурация (config.ts)

| Параметр | Значение |
|----------|----------|
| apiUrl | `http://localhost:8080` (из `VITE_API_URL`) |
| wsUrl | `ws://localhost:8080/ws/chat` |
| title | "ГК Проект" |
| subtitle | "Онлайн-консультант" |
| primaryColor | #2563EB (blue-600) |
| greeting | "Здравствуйте! Я AI-помощник «ГК Проект». Помогу с вопросами по монтажу котельных, отопления, водоснабжения, электрики и канализации. Чем могу помочь?" |
| placeholder | "Задайте вопрос об услугах..." |

## Демо-страница (App.tsx)

- Навбар: логотип "ГК" + название + телефон
- Hero: "Монтаж инженерных систем"
- 3 карточки преимуществ: "Без предоплат", "Гарантия до 10 лет", "1912+ объектов"
- Блок AI-консультанта (blue)
- ChatWidget в правом нижнем углу

## Правила кода

- Все компоненты — функциональные с TypeScript типами
- Props interface для каждого компонента
- Стили — ТОЛЬКО TailwindCSS (blue-600 основной цвет)
- API вызовы — только через `utils/api.ts`
- Streaming ответов — обязательно (SSE)
- Мобильная адаптивность: `max-sm:` breakpoint
- Accessibility: ARIA labels, keyboard navigation
- Все тексты — через `utils/config.ts`
