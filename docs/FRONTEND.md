# Frontend Widget — Техническая документация

## 1. Назначение

Встраиваемый чат-виджет для сайтов клиентов. Подключается одной строкой
JavaScript и предоставляет чат-интерфейс для взаимодействия с AI-агентом.

## 2. Стек технологий

| Технология    | Версия   | Назначение                    |
|---------------|----------|-------------------------------|
| React         | 18+      | UI фреймворк                  |
| TypeScript    | 5+       | Типизация                     |
| Vite          | 6+       | Сборщик                       |
| TailwindCSS   | 3+       | Стили                         |
| Zustand       | 5+       | State management              |

## 3. Структура модуля

```
frontend/
├── src/
│   ├── main.tsx                   # Точка входа React
│   ├── App.tsx                    # Корневой компонент
│   ├── widget.ts                  # Entry point для встраивания
│   ├── components/
│   │   ├── ChatWidget.tsx         # Главный контейнер виджета
│   │   ├── ChatWindow.tsx         # Окно чата
│   │   ├── ChatBubble.tsx         # Кнопка-пузырёк (открыть чат)
│   │   ├── MessageList.tsx        # Список сообщений
│   │   ├── MessageItem.tsx        # Одно сообщение (user/bot)
│   │   ├── InputBar.tsx           # Поле ввода + кнопка отправки
│   │   ├── TypingIndicator.tsx    # Индикатор "печатает..."
│   │   └── Header.tsx             # Заголовок окна чата
│   ├── hooks/
│   │   ├── useChat.ts             # Логика чата (отправка, получение)
│   │   ├── useWebSocket.ts        # WebSocket подключение
│   │   └── useSession.ts          # Управление сессией
│   ├── styles/
│   │   ├── globals.css            # TailwindCSS base
│   │   └── widget.css             # Стили виджета (scoped)
│   └── utils/
│       ├── api.ts                 # HTTP клиент (fetch wrapper)
│       ├── config.ts              # Конфигурация виджета
│       └── types.ts               # TypeScript типы
├── public/
│   └── index.html                 # Dev страница для тестирования
├── tests/
│   ├── ChatWidget.test.tsx
│   └── useChat.test.ts
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.js
├── Dockerfile
└── README.md
```

## 4. Компоненты UI

### 4.1 Иерархия компонентов

```
ChatWidget (корневой)
├── ChatBubble          — плавающая кнопка (правый нижний угол)
└── ChatWindow          — окно чата (показывается/скрывается)
    ├── Header          — заголовок + кнопка закрытия
    ├── MessageList     — скроллируемый список сообщений
    │   └── MessageItem — одно сообщение (user или bot)
    │       └── TypingIndicator — анимация при streaming
    └── InputBar        — поле ввода + кнопка отправки
```

### 4.2 Дизайн

- **Позиция**: fixed, правый нижний угол (кастомизируемо)
- **Размер**: 380x520px (адаптивно на мобильных)
- **Анимация**: плавное появление/скрытие (CSS transition)
- **Тема**: светлая по умолчанию, тёмная тема через конфиг
- **Цвета**: кастомизируемые через CSS переменные

### 4.3 Адаптивность

```
Desktop (>768px): виджет 380x520px, фиксирован справа внизу
Mobile  (<768px): виджет на весь экран (100vw x 100vh)
```

## 5. Хуки

### 5.1 useChat

```typescript
interface UseChatReturn {
  messages: Message[];
  isLoading: boolean;
  error: string | null;
  sendMessage: (text: string) => Promise<void>;
  clearHistory: () => void;
}

// Использование:
const { messages, isLoading, sendMessage } = useChat();
```

### 5.2 useWebSocket

```typescript
interface UseWebSocketReturn {
  isConnected: boolean;
  send: (data: any) => void;
  lastMessage: any;
  reconnect: () => void;
}
```

### 5.3 useSession

```typescript
interface UseSessionReturn {
  sessionId: string;
  isNewSession: boolean;
  resetSession: () => void;
}
// sessionId сохраняется в localStorage
```

## 6. Типы данных

```typescript
interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
  sources?: Source[];
  isStreaming?: boolean;
}

interface Source {
  title: string;
  chunk_id: string;
  score: number;
}

interface WidgetConfig {
  apiUrl: string;
  wsUrl: string;
  title: string;
  subtitle: string;
  primaryColor: string;
  position: 'bottom-right' | 'bottom-left';
  greeting: string;
  placeholder: string;
}
```

## 7. Встраивание на сайт

### 7.1 Вариант 1: Script tag

```html
<script
  src="https://your-domain.com/widget.js"
  data-api-url="https://api.your-domain.com"
  data-title="AI Помощник"
  data-color="#4F46E5"
></script>
```

### 7.2 Вариант 2: npm пакет

```typescript
import { AISaleWidget } from '@ai-sale/widget';

AISaleWidget.init({
  apiUrl: 'https://api.your-domain.com',
  title: 'AI Помощник',
  primaryColor: '#4F46E5',
});
```

## 8. Сборка для продакшна

Vite настроен для создания двух бандлов:

1. **widget.js** — самодостаточный скрипт для встраивания (UMD)
2. **React app** — SPA для разработки и тестирования

```javascript
// vite.config.ts — конфигурация для widget build
export default defineConfig({
  build: {
    lib: {
      entry: 'src/widget.ts',
      name: 'AISaleWidget',
      fileName: 'widget',
      formats: ['umd', 'es'],
    },
    rollupOptions: {
      // React включён в бандл для standalone виджета
    },
  },
});
```

## 9. Запуск

### Локально

```bash
cd frontend
npm install
npm run dev
# Открыть http://localhost:3000
```

### Сборка

```bash
npm run build         # Полная сборка
npm run build:widget  # Только виджет
```

### Docker

```bash
docker build -t ai-sale-frontend .
docker run -p 3000:80 ai-sale-frontend
```

## 10. Инструкции для AI-агента (Cursor)

При работе с Frontend:
1. Все компоненты — функциональные, с TypeScript типами
2. Стили — TailwindCSS, никакого inline CSS
3. Состояние — Zustand store, не prop drilling
4. API вызовы — только через `utils/api.ts`
5. Виджет должен быть полностью изолирован (Shadow DOM или CSS scope)
6. Все тексты — через конфиг (готовность к i18n)
7. Streaming ответы — обязательно, символ за символом
8. Мобильная адаптивность — обязательна
9. Accessibility: ARIA роли, keyboard navigation
