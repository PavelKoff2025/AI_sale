#!/usr/bin/env python3
"""
Load missing service pages into ChromaDB.
Pages were fetched via WebFetch because gkproject.ru is unreachable
from the local network. This script cleans the content, chunks it,
generates embeddings via OpenAI, and upserts into ChromaDB.
"""

import asyncio
import hashlib
import logging
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "parsing_agent"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PAGES = [
    {
        "url": "https://gkproject.ru/otoplenie/otoplenie_doma/",
        "title": "Отопление частного дома под ключ",
        "category": "otoplenie",
    },
    {
        "url": "https://gkproject.ru/otoplenie/montazh_kotelnoy_pod_klyuch/",
        "title": "Монтаж котельной под ключ",
        "category": "otoplenie",
    },
    {
        "url": "https://gkproject.ru/otoplenie/montazh_otopleniya/",
        "title": "Монтаж отопления",
        "category": "otoplenie",
    },
    {
        "url": "https://gkproject.ru/otoplenie/montazh_vodosnabzheniya/",
        "title": "Монтаж водоснабжения",
        "category": "otoplenie",
    },
    {
        "url": "https://gkproject.ru/otoplenie/montazh_teplogo_pola_pod_kluch/",
        "title": "Монтаж теплого пола под ключ",
        "category": "otoplenie",
    },
    {
        "url": "https://gkproject.ru/otoplenie/montazh-kotlov/",
        "title": "Монтаж котлов",
        "category": "otoplenie",
    },
    {
        "url": "https://gkproject.ru/otoplenie/montazh-radiatorov-otopleniya/",
        "title": "Монтаж радиаторов отопления",
        "category": "otoplenie",
    },
    {
        "url": "https://gkproject.ru/otoplenie/shef_montazh_sistem_ovk/",
        "title": "Шеф-монтаж систем ОВК",
        "category": "otoplenie",
    },
    {
        "url": "https://gkproject.ru/proektirovanie/sistem-otopleniya/",
        "title": "Проектирование систем отопления",
        "category": "proektirovanie",
    },
    {
        "url": "https://gkproject.ru/proektirovanie/vodosnabzheniya/",
        "title": "Проектирование водоснабжения",
        "category": "proektirovanie",
    },
    {
        "url": "https://gkproject.ru/servis/obsluzhivanie-kotelnyh/",
        "title": "Обслуживание котельных",
        "category": "servis",
    },
]

RAW_DIR = Path(__file__).resolve().parents[1] / "parsing_agent" / "data" / "raw" / "services"
CHROMA_DATA_DIR = os.getenv(
    "CHROMA_DATA_DIR",
    str(Path(__file__).resolve().parents[1] / "chroma_data"),
)


def clean_text(text: str) -> str:
    boilerplate_markers = [
        "## Как мы работаем:",
        "## Нужна консультация?",
        "## Мы можем монтировать, проектировать и снабжать",
        "## 8 фактов о нас",
        "Вам уже сделали предложение по отоплению?",
        "Ваше Имя",
        "Оставить заявку",
    ]
    for marker in boilerplate_markers:
        idx = text.find(marker)
        if idx != -1:
            remaining = text[idx:]
            if remaining.count(marker) == 1 and len(remaining) > len(text) * 0.3:
                text = text[:idx]
                break

    text = re.sub(r"\[Контакты\]\(https://gkproject\.ru/contacts/\)", "", text)
    text = re.sub(r"ООО \"ГК Проект\"", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()
    return text


def chunk_text(text: str, metadata: dict, chunk_size: int = 2000, overlap: int = 200) -> list[dict]:
    separators = ["\n\n", "\n", ". ", " "]
    chunks = _recursive_split(text, separators, chunk_size, overlap)

    result = []
    for i, chunk_text_piece in enumerate(chunks):
        if len(chunk_text_piece.strip()) < 50:
            continue
        chunk_id = hashlib.md5(chunk_text_piece.encode()).hexdigest()
        result.append({
            "id": chunk_id,
            "text": chunk_text_piece.strip(),
            "metadata": {
                **metadata,
                "chunk_index": i,
                "company": "ГК Проект",
            },
        })
    return result


def _recursive_split(text: str, separators: list[str], chunk_size: int, overlap: int) -> list[str]:
    if len(text) <= chunk_size:
        return [text]

    sep = separators[0] if separators else " "
    parts = text.split(sep)
    chunks = []
    current = ""

    for part in parts:
        candidate = current + sep + part if current else part
        if len(candidate) > chunk_size and current:
            chunks.append(current)
            overlap_text = current[-overlap:] if overlap else ""
            current = overlap_text + sep + part if overlap_text else part
        else:
            current = candidate

    if current:
        chunks.append(current)

    if len(separators) > 1:
        refined = []
        for c in chunks:
            if len(c) > chunk_size:
                refined.extend(_recursive_split(c, separators[1:], chunk_size, overlap))
            else:
                refined.append(c)
        return refined

    return chunks


async def main():
    import chromadb
    from openai import OpenAI

    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        logger.error("OPENAI_API_KEY not set")
        sys.exit(1)

    openai_client = OpenAI(api_key=api_key)
    chroma_client = chromadb.PersistentClient(path=CHROMA_DATA_DIR)
    collection = chroma_client.get_or_create_collection(
        name="ai_sale_knowledge",
        metadata={"hnsw:space": "cosine"},
    )

    before_count = collection.count()
    logger.info("ChromaDB before: %d documents", before_count)

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    all_chunks = []
    for page in PAGES:
        md_file = RAW_DIR / f"{page['url'].rstrip('/').split('/')[-1]}.md"
        if not md_file.exists():
            logger.warning("File not found: %s — skipping", md_file)
            continue

        raw_text = md_file.read_text(encoding="utf-8")
        cleaned = clean_text(raw_text)
        metadata = {
            "url": page["url"],
            "title": page["title"],
            "category": page["category"],
            "source": page["url"],
        }
        chunks = chunk_text(cleaned, metadata)
        all_chunks.extend(chunks)
        logger.info("  %s: %d chunks", page["title"], len(chunks))

    if not all_chunks:
        logger.error("No chunks to load!")
        sys.exit(1)

    logger.info("Total chunks to load: %d", len(all_chunks))

    batch_size = 100
    loop = asyncio.get_running_loop()

    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i:i + batch_size]
        texts = [c["text"] for c in batch]
        ids = [c["id"] for c in batch]
        metadatas = [c["metadata"] for c in batch]

        response = await loop.run_in_executor(
            None,
            lambda t=texts: openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=t,
            ),
        )
        embeddings = [item.embedding for item in response.data]

        await loop.run_in_executor(
            None,
            lambda: collection.upsert(
                ids=ids,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
            ),
        )
        logger.info("  Loaded batch %d-%d / %d", i + 1, i + len(batch), len(all_chunks))

    after_count = collection.count()
    logger.info("ChromaDB after: %d documents (+%d new)", after_count, after_count - before_count)
    logger.info("Done!")


if __name__ == "__main__":
    asyncio.run(main())
