import logging
import os
from pathlib import Path

import chromadb
from openai import OpenAI

from app.processors.chunker import Chunk

logger = logging.getLogger(__name__)

CHROMA_PERSIST_DIR = str(Path(__file__).resolve().parents[3] / "chroma_data")


class ChromaLoader:
    def __init__(self, config: dict):
        self.config = config
        chroma_host = os.getenv("CHROMA_HOST", "localhost")
        chroma_port = int(os.getenv("CHROMA_PORT", "8000"))
        collection_name = config.get("chroma", {}).get("collection", "ai_sale_knowledge")

        try:
            self.chroma_client = chromadb.HttpClient(host=chroma_host, port=chroma_port)
            self.chroma_client.heartbeat()
        except Exception:
            logger.warning(
                "ChromaDB server not available, using PersistentClient at %s",
                CHROMA_PERSIST_DIR,
            )
            self.chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)

        self.collection = self.chroma_client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        api_key = os.getenv("OPENAI_API_KEY", "")
        if api_key:
            self.openai_client = OpenAI(api_key=api_key)
        else:
            self.openai_client = None
            logger.warning("OPENAI_API_KEY not set — embedding generation disabled")
        self.embedding_model = config.get("embeddings", {}).get("model", "text-embedding-3-small")
        self.batch_size = config.get("embeddings", {}).get("batch_size", 100)

    async def load(self, chunks: list[Chunk]):
        if not self.openai_client:
            raise RuntimeError("Cannot load chunks: OPENAI_API_KEY is not set")

        seen_ids: set[str] = set()
        unique_chunks: list[Chunk] = []
        for c in chunks:
            if c.chunk_id not in seen_ids:
                seen_ids.add(c.chunk_id)
                unique_chunks.append(c)

        if len(unique_chunks) < len(chunks):
            logger.info(
                "Deduplicated: %d → %d chunks (%d duplicates removed)",
                len(chunks), len(unique_chunks), len(chunks) - len(unique_chunks),
            )

        logger.info("Loading %d chunks to ChromaDB...", len(unique_chunks))

        for i in range(0, len(unique_chunks), self.batch_size):
            batch = unique_chunks[i : i + self.batch_size]
            texts = [c.text for c in batch]
            ids = [c.chunk_id for c in batch]
            metadatas = [c.metadata for c in batch]

            response = self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=texts,
            )
            embeddings = [item.embedding for item in response.data]

            self.collection.upsert(
                ids=ids,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
            )
            logger.info("Loaded batch %d-%d / %d", i + 1, i + len(batch), len(chunks))

        logger.info("All chunks loaded. Total in collection: %d", self.collection.count())

    def get_stats(self) -> dict:
        return {
            "collection": self.collection.name,
            "count": self.collection.count(),
        }

    def clear(self):
        name = self.collection.name
        self.chroma_client.delete_collection(name)
        self.collection = self.chroma_client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("Collection '%s' cleared.", name)
