# Parsing Agent — Сбор данных для RAG

Python-агент для парсинга данных из веб-сайтов, PDF, DOCX.
Очищает текст, разбивает на чанки, создаёт embeddings и загружает в ChromaDB.

---

## Содержимое

```
parsing_agent/
├── app/
│   ├── __init__.py
│   ├── main.py                      # CLI точка входа — аргументы и запуск pipeline
│   ├── pipeline.py                  # Pipeline — оркестрация: parse → clean → chunk → load
│   │
│   ├── parsers/                     # Парсеры источников данных
│   │   ├── __init__.py
│   │   ├── base.py                  # BaseParser (ABC) + ParsedDocument (dataclass)
│   │   ├── web_parser.py            # WebParser — HTML страницы через requests + BeautifulSoup
│   │   ├── pdf_parser.py            # PDFParser — извлечение текста из PDF через PyPDF2
│   │   └── docx_parser.py           # DOCXParser — извлечение текста из DOCX через python-docx
│   │
│   ├── processors/                  # Обработчики текста
│   │   ├── __init__.py
│   │   ├── cleaner.py               # TextCleaner — удаление HTML, пробелов, нормализация
│   │   └── chunker.py               # TextChunker — разбивка на чанки + Chunk (dataclass)
│   │
│   └── loaders/                     # Загрузчики в векторную БД
│       ├── __init__.py
│       └── chroma_loader.py         # ChromaLoader — embeddings + upsert в ChromaDB
│
├── data/
│   ├── raw/                         # Сырые файлы (PDF, DOCX) — git-ignored
│   │   └── .gitkeep
│   └── processed/                   # Обработанные чанки (chunks.json)
│       └── .gitkeep
│
├── configs/
│   ├── sources.yaml                 # Конфиг источников: URL, файлы, паттерны
│   └── processing.yaml              # Конфиг обработки: chunk_size, overlap, embeddings
│
├── tests/
│   └── __init__.py
├── requirements.txt                 # Python зависимости
└── Dockerfile                       # Docker образ
```

---

## Что делает каждый файл

### `app/main.py` — CLI точка входа

Парсинг аргументов командной строки и запуск pipeline:

| Аргумент | По умолчанию | Описание |
|----------|-------------|----------|
| `--config` | `configs/sources.yaml` | Путь к конфигу источников |
| `--processing-config` | `configs/processing.yaml` | Путь к конфигу обработки |
| `--parse-only` | — | Только спарсить и сохранить в JSON (без загрузки в БД) |
| `--load-only` | — | Только загрузить готовые чанки из JSON |
| `--output` | `data/processed/` | Папка вывода для `--parse-only` |
| `--input` | `data/processed/` | Папка ввода для `--load-only` |
| `--clear-collection` | — | Очистить коллекцию ChromaDB |
| `--stats` | — | Показать статистику коллекции |

### `app/pipeline.py` — Оркестратор

Класс `Pipeline` — управляет полным процессом:

```
run_full():
  1. _parse_all()  → список ParsedDocument
  2. _process()    → список Chunk (clean + chunk)
  3. loader.load() → embeddings + upsert в ChromaDB
```

Дополнительные режимы:
- `run_parse_only(output)` — парсинг + обработка → сохранить в `chunks.json`
- `run_load_only(input)` — загрузить из `chunks.json` → ChromaDB
- `show_stats()` — количество документов в коллекции
- `clear_collection()` — полная очистка коллекции

Карта парсеров: `{"web": WebParser, "pdf": PDFParser, "docx": DOCXParser}`

---

### Парсеры (`app/parsers/`)

#### `base.py` — Базовый класс

```python
@dataclass
class ParsedDocument:
    text: str           # Извлечённый текст
    metadata: dict      # source, url, title, file, ...
    source_type: str    # "web" | "pdf" | "docx"

class BaseParser(ABC):
    async def parse(self, source_config: dict) -> list[ParsedDocument]
```

Каждый парсер возвращает список `ParsedDocument`.

#### `web_parser.py` — Парсинг веб-страниц

Класс `WebParser`:

1. Обходит все URL из `source_config["urls"]`
2. Для каждого URL:
   - GET запрос с User-Agent `"AI-Sale-Parser/1.0"`
   - BeautifulSoup + lxml парсер
   - Удаляет `<script>`, `<style>`, `<nav>`, `<footer>`, `<header>`
   - Извлекает текст из `h1-h4`, `p`, `li`, `td`
   - Сохраняет title страницы в metadata
3. Задержка между запросами (`delay_seconds`, default 1.5s)
4. Ошибки логируются, парсинг продолжается

#### `pdf_parser.py` — Парсинг PDF

Класс `PDFParser`:

1. Открывает PDF через `PyPDF2.PdfReader`
2. Извлекает текст со всех страниц
3. Объединяет через `\n\n`
4. Metadata: filename, title, total_pages

#### `docx_parser.py` — Парсинг DOCX

Класс `DOCXParser`:

1. Открывает DOCX через `python-docx.Document`
2. Извлекает все непустые параграфы
3. Объединяет через `\n\n`
4. Metadata: filename, title

---

### Процессоры (`app/processors/`)

#### `cleaner.py` — Очистка текста

Класс `TextCleaner`:

| Шаг | Действие |
|-----|----------|
| 1 | `html.unescape()` — декодирование HTML entities |
| 2 | Удаление HTML тегов (regex) |
| 3 | Нормализация пробелов — max 2 переноса, max 1 пробел |
| 4 | Strip + обрезка по `max_chunk_length * 10` |

Настраивается через `processing.yaml → cleaning`.

#### `chunker.py` — Разбивка на чанки

Два класса:

**`Chunk` (dataclass)**:
- `text` — текст чанка
- `metadata` — метаданные источника + `chunk_index`, `total_chunks`
- `chunk_id` — MD5 хэш текста (первые 12 символов) для дедупликации

**`TextChunker`**:
- Использует LangChain `RecursiveCharacterTextSplitter`
- Настройки из `processing.yaml → chunking`:
  - `chunk_size`: 500 символов
  - `chunk_overlap`: 50 символов
  - `separators`: `["\n\n", "\n", ". ", " "]`

---

### Загрузчик (`app/loaders/`)

#### `chroma_loader.py` — Загрузка в ChromaDB

Класс `ChromaLoader`:

**Инициализация**:
- Подключается к ChromaDB (HttpClient или EphemeralClient как fallback)
- Создаёт/получает коллекцию с `cosine` метрикой
- Инициализирует OpenAI клиент для embeddings

**`load(chunks)`** — загрузка батчами:
1. Берёт батч до 100 чанков
2. Создаёт embeddings через OpenAI `text-embedding-3-small`
3. Upsert в ChromaDB (ids + documents + embeddings + metadatas)
4. Логирует прогресс

**`get_stats()`** — `{collection, count}`

**`clear()`** — удаляет и пересоздаёт коллекцию

---

### Конфиги (`configs/`)

#### `sources.yaml` — Источники данных

```yaml
sources:
  - name: "company_website"     # Имя источника
    type: "web"                 # Тип: web | pdf | docx
    urls:                       # Список URL для парсинга
      - "https://example.com/"
    depth: 1                    # Глубина crawling
    include_patterns: [...]     # Какие URL включать
    exclude_patterns: [...]     # Какие URL исключать
    delay_seconds: 1.5          # Задержка между запросами
```

#### `processing.yaml` — Параметры обработки

| Секция | Параметр | Значение | Описание |
|--------|----------|----------|----------|
| chunking | chunk_size | 500 | Размер чанка в символах |
| chunking | chunk_overlap | 50 | Перекрытие между чанками |
| chunking | strategy | recursive | Стратегия разбивки |
| cleaning | min_chunk_length | 50 | Минимум символов (отбросить мусор) |
| cleaning | max_chunk_length | 2000 | Максимум символов |
| embeddings | model | text-embedding-3-small | Модель OpenAI |
| embeddings | batch_size | 100 | Чанков за один API запрос |
| chroma | collection | ai_sale_knowledge | Имя коллекции |
| chroma | distance_metric | cosine | Метрика расстояния |

---

## Pipeline (визуально)

```
sources.yaml          processing.yaml
     │                      │
     ▼                      ▼
 ┌────────┐          ┌────────────┐
 │ WebParser │         │  TextCleaner │
 │ PDFParser │────────▶│  TextChunker │
 │ DOCXParser│         └──────┬───────┘
 └────────┘                  │
                             ▼
                      ┌────────────┐
                      │ ChromaLoader │
                      │  embeddings  │
                      │  + upsert    │
                      └──────┬───────┘
                             │
                             ▼
                        ChromaDB
                    (ai_sale_knowledge)
```

---

## Запуск

```bash
cd parsing_agent
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Полный pipeline
python -m app.main

# Только парсинг (без загрузки)
python -m app.main --parse-only --output data/processed/

# Только загрузка готовых чанков
python -m app.main --load-only --input data/processed/

# Статистика
python -m app.main --stats

# Очистка коллекции
python -m app.main --clear-collection
```
