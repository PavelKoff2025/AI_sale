# Агент Парсер — подчинён Тимлиду

## Роль

Агент "Парсер" подчинён Тимлиду. Задача: парсинг сайта gkproject.ru,
извлечение структурированных данных, загрузка в RAG базу ChromaDB.

## Стек

Python 3.11+, BeautifulSoup4, PyPDF2, python-docx, LangChain, ChromaDB, OpenAI SDK

## Сайт gkproject.ru — структура

- Bitrix CMS, пагинация через `?PAGEN_1=N`
- Главная `/` — услуги, кейсы, FAQ, команда, статистика
- Контакты `/contacts/` — телефон, email, адрес, юр. данные
- Портфолио `/nashi-raboty/` — 5 страниц с кейсами
- Отзывы `/reviews/` — 2 страницы + отдельные страницы отзывов
- Блог `/blog/` — 4 страницы + отдельные статьи

## Структура модуля

```
parsing_agent/
├── app/
│   ├── main.py                      # CLI точка входа — аргументы и запуск pipeline
│   ├── pipeline.py                  # Pipeline — оркестрация: parse → clean → chunk → load
│   ├── parsers/
│   │   ├── base.py                  # BaseParser (ABC) + ParsedDocument (dataclass)
│   │   ├── gkproject_parser.py      # GKProjectParser — специализированный под gkproject.ru
│   │   ├── web_parser.py            # WebParser — универсальный HTML парсер
│   │   ├── pdf_parser.py            # PDFParser — извлечение текста из PDF
│   │   └── docx_parser.py           # DOCXParser — извлечение текста из DOCX
│   ├── processors/
│   │   ├── cleaner.py               # TextCleaner — удаление HTML, пробелов, нормализация
│   │   └── chunker.py               # TextChunker — разбивка на чанки + Chunk (dataclass)
│   └── loaders/
│       └── chroma_loader.py         # ChromaLoader — embeddings + upsert в ChromaDB
├── data/
│   ├── raw/                         # Сырые файлы (PDF, DOCX) — git-ignored
│   └── processed/                   # Обработанные чанки (chunks.json)
├── configs/
│   ├── sources.yaml                 # Конфиг источников: все URL gkproject.ru
│   └── processing.yaml             # Конфиг обработки: chunk_size, overlap, embeddings
├── requirements.txt
└── Dockerfile
```

## GKProjectParser

Специализированный парсер для gkproject.ru (`app/parsers/gkproject_parser.py`).

### Экстракторы по категориям

| Категория | Метод | Что извлекает |
|-----------|-------|---------------|
| general | `_extract_general()` | Вызывает все подэкстракторы для главной страницы |
| services | `_extract_services()` | 5 направлений, 30+ подуслуг |
| process | `_extract_work_process()` | 6 шагов работы компании |
| stats | `_extract_stats()` | 1912 объектов, 12 бригад, 663920 км труб и т.д. |
| team | `_extract_team()` | 10 сотрудников с должностями |
| faq | `_extract_faq()` | 5 вопросов-ответов |
| advantages | `_extract_advantages()` | 9 преимуществ (гарантия, без предоплат, оплата по факту) |
| contacts | `_extract_contacts()` | Телефон, email, адрес, ИНН, ОГРН |
| portfolio | `_extract_portfolio()` | Кейсы: тип дома, этажность, сроки, описание, стоимость |
| reviews | `_extract_reviews()` | Отзывы клиентов |
| blog | `_extract_blog()` | Статьи блога |

### Авто-обнаружение ссылок

Для reviews и blog включён `follow_links: true` — парсер автоматически находит
и обходит внутренние ссылки на отдельные страницы отзывов и статей.

## Pipeline

```
sources.yaml → GKProjectParser → TextCleaner → TextChunker → ChromaLoader → ChromaDB
```

1. **Parse**: GKProjectParser обходит все URL, извлекает ParsedDocument (text + metadata)
2. **Clean**: TextCleaner удаляет HTML, нормализует пробелы
3. **Chunk**: TextChunker разбивает на чанки (500 символов, overlap 50)
4. **Embed**: ChromaLoader создаёт embeddings через OpenAI `text-embedding-3-small` (батчами по 100)
5. **Load**: Upsert в ChromaDB коллекцию `ai_sale_knowledge`

## Категории данных

| Категория | Описание | Источник |
|-----------|----------|----------|
| services | 5 направлений: котельные, отопление, водоснабжение, электрика, канализация | `/` |
| portfolio | Кейсы с полями: тип дома, этажность, сроки, описание, стоимость | `/nashi-raboty/` |
| reviews | Отзывы клиентов | `/reviews/` |
| contacts | Телефон, email, адрес, юр. информация | `/contacts/` |
| process | 6 шагов работы | `/` |
| team | 10 сотрудников | `/` |
| faq | 5 вопросов-ответов | `/` |
| advantages | 9 преимуществ | `/` |
| blog | Статьи | `/blog/` |

## Конфигурация

### sources.yaml

14 URL gkproject.ru, разбитых по секциям:
- homepage (1 URL)
- contacts (1 URL)
- portfolio (5 страниц пагинации)
- reviews (2 страницы + follow_links)
- blog (4 страницы + follow_links)

### processing.yaml

| Параметр | Значение |
|----------|----------|
| chunk_size | 500 символов |
| chunk_overlap | 50 |
| strategy | recursive |
| embedding model | text-embedding-3-small |
| batch_size | 100 |
| collection | ai_sale_knowledge |
| distance_metric | cosine |

## CLI команды

```bash
python -m app.main                          # Полный pipeline
python -m app.main --parse-only             # Только парсинг → JSON
python -m app.main --load-only              # Загрузить из JSON → ChromaDB
python -m app.main --stats                  # Статистика коллекции
python -m app.main --clear-collection       # Очистить коллекцию
```

## Правила

1. Не хардкодить URL — всё из `sources.yaml`
2. Rate limiting обязателен (`delay_seconds: 1.0`)
3. Все данные с metadata: source, url, title, category, company
4. При ошибке — логировать и продолжать (не ронять pipeline)
5. Дедупликация по `chunk_id` (MD5 hash текста)
6. Каждый парсер — отдельный класс, наследник BaseParser
7. Embedding батчами — экономим API вызовы
