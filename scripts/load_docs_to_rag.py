"""
Загрузка файлов из docs/ в RAG базу знаний (ChromaDB).
Разбивает документы на семантические чанки и генерирует embeddings.

Использование:
  cd AI_sale
  python scripts/load_docs_to_rag.py
"""

import hashlib
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

import chromadb
from openai import OpenAI

CHROMA_PERSIST_DIR = str(ROOT / "chroma_data")
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION", "ai_sale_knowledge")
EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

DOCS_TO_LOAD = {
    ROOT / "docs" / "Companie": {
        "source": "docs/Companie",
        "url": "https://gkproject.ru",
    },
    ROOT / "docs" / "FAQ": {
        "source": "docs/FAQ",
        "url": "https://gkproject.ru",
    },
}


def split_by_sections(text: str, base_metadata: dict) -> list[dict]:
    """Разбивает текст по заголовкам ## и ###, сохраняя контекст."""
    chunks = []
    sections = re.split(r'\n(?=#{1,3}\s)', text)

    current_h2 = ""
    for section in sections:
        section = section.strip()
        if not section:
            continue

        h2_match = re.match(r'^##\s+(.+)', section)
        h3_match = re.match(r'^###\s+(.+)', section)

        if h2_match:
            current_h2 = h2_match.group(1).strip().strip('*')
        title = ""
        if h3_match:
            title = h3_match.group(1).strip().strip('*')
        elif h2_match:
            title = current_h2
        else:
            title = current_h2 or "Общая информация"

        if len(section) > 1500:
            sub_parts = split_long_section(section)
            for j, part in enumerate(sub_parts):
                chunk_id = hashlib.md5(part.encode()).hexdigest()[:12]
                chunks.append({
                    "id": chunk_id,
                    "text": part,
                    "metadata": {
                        **base_metadata,
                        "title": title,
                        "category": current_h2 or "company_info",
                        "chunk_index": len(chunks),
                    },
                })
        else:
            chunk_id = hashlib.md5(section.encode()).hexdigest()[:12]
            chunks.append({
                "id": chunk_id,
                "text": section,
                "metadata": {
                    **base_metadata,
                    "title": title,
                    "category": current_h2 or "company_info",
                    "chunk_index": len(chunks),
                },
            })

    return chunks


def split_by_qa(text: str, base_metadata: dict) -> list[dict]:
    """Разбивает FAQ на пары вопрос-ответ."""
    chunks = []
    current_section = ""
    qa_blocks = re.split(r'\n(?=\*\*[^*]+\*\*\s*\n)', text)

    for block in qa_blocks:
        block = block.strip()
        if not block:
            continue

        h2_match = re.match(r'^##\s+(.+)', block)
        if h2_match:
            current_section = h2_match.group(1).strip()
            rest = block[h2_match.end():].strip()
            if not rest:
                continue
            block = rest

        question_match = re.match(r'\*\*(.+?)\*\*', block)
        title = question_match.group(1).strip() if question_match else current_section

        chunk_id = hashlib.md5(block.encode()).hexdigest()[:12]
        chunks.append({
            "id": chunk_id,
            "text": block,
            "metadata": {
                **base_metadata,
                "title": title,
                "category": current_section or "faq",
                "chunk_index": len(chunks),
            },
        })

    return chunks


def split_long_section(text: str, max_len: int = 1200) -> list[str]:
    """Разбивает длинные секции по абзацам."""
    paragraphs = text.split("\n\n")
    parts = []
    current = ""
    for p in paragraphs:
        if len(current) + len(p) > max_len and current:
            parts.append(current.strip())
            current = p
        else:
            current = current + "\n\n" + p if current else p
    if current.strip():
        parts.append(current.strip())
    return parts


def main():
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set in .env")
        sys.exit(1)

    openai_client = OpenAI(api_key=api_key)

    try:
        chroma_host = os.getenv("CHROMA_HOST", "localhost") or "localhost"
        chroma_port = int(os.getenv("CHROMA_PORT", "8000") or "8000")
        chroma_client = chromadb.HttpClient(
            host=chroma_host,
            port=chroma_port,
        )
        chroma_client.heartbeat()
        print(f"Connected to ChromaDB server at {chroma_host}:{chroma_port}")
    except Exception:
        print(f"ChromaDB server unavailable, using PersistentClient at {CHROMA_PERSIST_DIR}")
        chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)

    collection = chroma_client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    print(f"Collection '{COLLECTION_NAME}': {collection.count()} documents before loading")
    print()

    all_chunks = []

    for filepath, meta in DOCS_TO_LOAD.items():
        if not filepath.exists():
            print(f"SKIP: {filepath} not found")
            continue

        text = filepath.read_text(encoding="utf-8")
        filename = filepath.name
        print(f"Processing: {filename} ({len(text)} chars)")

        base_metadata = {
            "source": meta["source"],
            "url": meta["url"],
        }

        if "FAQ" in filename:
            chunks = split_by_qa(text, base_metadata)
        else:
            chunks = split_by_sections(text, base_metadata)

        print(f"  → {len(chunks)} chunks")
        for c in chunks[:3]:
            print(f"     [{c['metadata']['title'][:50]}] {c['text'][:80]}...")
        if len(chunks) > 3:
            print(f"     ... and {len(chunks) - 3} more")

        all_chunks.extend(chunks)

    if not all_chunks:
        print("No chunks to load!")
        sys.exit(1)

    seen_ids = set()
    unique_chunks = []
    for c in all_chunks:
        if c["id"] not in seen_ids:
            seen_ids.add(c["id"])
            unique_chunks.append(c)

    print(f"\nTotal: {len(unique_chunks)} unique chunks (dedup: {len(all_chunks) - len(unique_chunks)} removed)")
    print("Generating embeddings and loading to ChromaDB...")

    batch_size = 50
    for i in range(0, len(unique_chunks), batch_size):
        batch = unique_chunks[i:i + batch_size]
        texts = [c["text"] for c in batch]
        ids = [c["id"] for c in batch]
        metadatas = [c["metadata"] for c in batch]

        response = openai_client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=texts,
        )
        embeddings = [item.embedding for item in response.data]

        collection.upsert(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        print(f"  Batch {i + 1}-{i + len(batch)} / {len(unique_chunks)} loaded")

    print(f"\nDone! Collection '{COLLECTION_NAME}' now has {collection.count()} documents")


if __name__ == "__main__":
    main()
