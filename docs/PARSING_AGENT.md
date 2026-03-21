# Parsing Agent — Техническая документация

## 1. Назначение

Агент парсинга данных. Собирает информацию из различных источников
(веб-сайты, PDF, DOCX, CSV), обрабатывает её, разбивает на чанки,
создаёт embeddings и загружает в векторную базу данных для RAG.

## 2. Стек технологий

| Технология       | Версия | Назначение                       |
|------------------|--------|----------------------------------|
| Python           | 3.11+  | Язык                             |
| BeautifulSoup4   | 4.12+  | Парсинг HTML                     |
| Requests         | 2.32+  | HTTP запросы                     |
| PyPDF2           | 3.0+   | Извлечение текста из PDF         |
| python-docx      | 1.1+   | Извлечение текста из DOCX        |
| LangChain        | 0.3+   | Text splitting, embeddings       |
| OpenAI SDK       | 1.60+  | Создание embeddings              |
| ChromaDB         | 0.5+   | Загрузка в векторную БД          |
| Schedule         | 1.2+   | Планирование периодических задач |
| Playwright       | 1.49+  | Парсинг JS-rendered страниц      |

## 3. Структура модуля

```
parsing_agent/
├── app/
│   ├── __init__.py
│   ├── main.py                    # Точка входа
│   ├── pipeline.py                # Главный pipeline обработки
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── base.py                # BaseParser (абстрактный)
│   │   ├── web_parser.py          # Парсинг веб-страниц
│   │   ├── pdf_parser.py          # Парсинг PDF файлов
│   │   ├── docx_parser.py         # Парсинг DOCX файлов
│   │   └── csv_parser.py          # Парсинг CSV/Excel
│   ├── processors/
│   │   ├── __init__.py
│   │   ├── cleaner.py             # Очистка текста
│   │   ├── chunker.py             # Разбиение на чанки
│   │   └── metadata_extractor.py  # Извлечение метаданных
│   └── loaders/
│       ├── __init__.py
│       ├── chroma_loader.py       # Загрузка в ChromaDB
│       └── embeddings.py          # Создание embeddings
├── data/
│   ├── raw/                       # Сырые данные (файлы, HTML)
│   └── processed/                 # Обработанные чанки (JSON)
├── configs/
│   ├── sources.yaml               # Конфиг источников данных
│   └── processing.yaml            # Конфиг обработки
├── tests/
│   ├── test_parsers.py
│   ├── test_chunker.py
│   └── test_pipeline.py
├── requirements.txt
├── Dockerfile
└── README.md
```

## 4. Pipeline обработки

```
                  ┌──────────────┐
                  │   sources    │
                  │   .yaml      │
                  └──────┬───────┘
                         │
                         ▼
              ┌──────────────────┐
              │    PARSERS       │
              │  web / pdf /     │
              │  docx / csv      │
              └────────┬─────────┘
                       │ raw text + metadata
                       ▼
              ┌──────────────────┐
              │   CLEANER        │
              │  - strip HTML    │
              │  - remove noise  │
              │  - normalize     │
              └────────┬─────────┘
                       │ clean text
                       ▼
              ┌──────────────────┐
              │   CHUNKER        │
              │  - split text    │
              │  - overlap       │
              │  - token count   │
              └────────┬─────────┘
                       │ chunks[]
                       ▼
              ┌──────────────────┐
              │  EMBEDDINGS      │
              │  OpenAI API      │
              │  text-embedding  │
              │  -3-small        │
              └────────┬─────────┘
                       │ chunks + vectors
                       ▼
              ┌──────────────────┐
              │  CHROMA LOADER   │
              │  upsert to       │
              │  collection      │
              └──────────────────┘
```

## 5. Конфигурация источников

### sources.yaml

```yaml
sources:
  - name: "company_website"
    type: "web"
    urls:
      - "https://example.com/"
      - "https://example.com/services"
      - "https://example.com/pricing"
      - "https://example.com/about"
    depth: 2                    # глубина crawling
    include_patterns:
      - "/services/*"
      - "/products/*"
    exclude_patterns:
      - "/blog/*"
      - "/admin/*"

  - name: "product_catalog"
    type: "pdf"
    path: "data/raw/catalog.pdf"

  - name: "faq"
    type: "docx"
    path: "data/raw/faq.docx"

  - name: "price_list"
    type: "csv"
    path: "data/raw/prices.csv"
    columns:
      - "product_name"
      - "description"
      - "price"
```

### processing.yaml

```yaml
processing:
  chunking:
    strategy: "recursive"       # recursive | sentence | fixed
    chunk_size: 500             # токенов
    chunk_overlap: 50           # перекрытие
    separators:
      - "\n\n"
      - "\n"
      - ". "
      - " "

  cleaning:
    remove_html: true
    remove_extra_whitespace: true
    min_chunk_length: 50        # символов — отбросить мусор
    max_chunk_length: 2000      # символов

  embeddings:
    model: "text-embedding-3-small"
    batch_size: 100             # чанков за один API запрос
    dimensions: 1536

  chroma:
    collection: "ai_sale_knowledge"
    distance_metric: "cosine"
```

## 6. Parsers

### 6.1 BaseParser (абстрактный)

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class ParsedDocument:
    text: str
    metadata: dict       # source, url, title, etc.
    source_type: str     # web, pdf, docx, csv

class BaseParser(ABC):
    @abstractmethod
    async def parse(self, source_config: dict) -> list[ParsedDocument]:
        pass
```

### 6.2 WebParser

- Использует `requests` + `BeautifulSoup` для статических страниц
- `Playwright` для JS-rendered SPA
- Извлекает: title, h1-h6, paragraphs, lists, tables
- Рекурсивный crawling с учётом `depth` и `include_patterns`
- Respectful: robots.txt, delays между запросами

### 6.3 PDFParser

- PyPDF2 для извлечения текста
- Сохраняет metadata: filename, page_number, total_pages

### 6.4 DOCXParser

- python-docx для извлечения параграфов
- Обрабатывает заголовки, списки, таблицы

### 6.5 CSVParser

- pandas для чтения CSV/Excel
- Каждая строка → отдельный документ с колонками в metadata

## 7. Processors

### 7.1 Cleaner

```python
class TextCleaner:
    def clean(self, text: str) -> str:
        # 1. Удалить HTML теги
        # 2. Удалить лишние пробелы/переносы
        # 3. Нормализовать Unicode
        # 4. Удалить спецсимволы (но сохранить пунктуацию)
        return cleaned_text
```

### 7.2 Chunker

```python
class TextChunker:
    def __init__(self, chunk_size=500, chunk_overlap=50):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=tiktoken_len,
        )

    def chunk(self, document: ParsedDocument) -> list[Chunk]:
        chunks = self.splitter.split_text(document.text)
        return [
            Chunk(
                text=chunk,
                metadata={
                    **document.metadata,
                    "chunk_index": i,
                    "total_chunks": len(chunks)
                }
            )
            for i, chunk in enumerate(chunks)
        ]
```

## 8. Запуск

### Одноразовая загрузка

```bash
cd parsing_agent
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Загрузка данных
python -m app.main --config configs/sources.yaml
```

### Периодический парсинг

```bash
# Запуск с расписанием (каждые 24 часа)
python -m app.main --schedule --interval 86400
```

### Docker

```bash
docker build -t ai-sale-parser .
docker run --env-file ../.env -v ./data:/app/data ai-sale-parser
```

## 9. CLI команды

```bash
# Полный pipeline
python -m app.main

# Только парсинг (без загрузки в БД)
python -m app.main --parse-only --output data/processed/

# Только загрузка уже обработанных данных
python -m app.main --load-only --input data/processed/

# Очистка коллекции
python -m app.main --clear-collection

# Статистика коллекции
python -m app.main --stats
```

## 10. Инструкции для AI-агента (Cursor)

При работе с Parsing Agent:
1. Каждый парсер наследуется от `BaseParser` — единый интерфейс
2. Конфиги — только YAML, не хардкодить URL и пути
3. Rate limiting обязателен для веб-парсинга (min 1s между запросами)
4. Embedding батчами (до 100 чанков) — экономим API вызовы
5. Логирование каждого шага pipeline (количество, ошибки)
6. Дедупликация чанков перед загрузкой (по hash содержимого)
7. Обязательная обработка ошибок: битые PDF, недоступные URL
8. `data/raw/` — git-ignored, `data/processed/` — опционально в git
9. Тесты с мок-данными, не с реальными URL
