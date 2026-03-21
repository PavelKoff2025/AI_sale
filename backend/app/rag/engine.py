import logging
import os
from pathlib import Path

import chromadb

from app.core.config import settings

logger = logging.getLogger(__name__)

CHROMA_PERSIST_DIR = os.getenv(
    "CHROMA_DATA_DIR",
    str(Path(__file__).resolve().parents[3] / "chroma_data"),
)


class RAGEngine:
    def __init__(self):
        self.chroma_client: chromadb.ClientAPI | None = None
        self.collection = None

    async def initialize(self):
        try:
            self.chroma_client = chromadb.HttpClient(
                host=settings.chroma_host,
                port=settings.chroma_port,
            )
            self.chroma_client.heartbeat()
            logger.info("Connected to ChromaDB server at %s:%s", settings.chroma_host, settings.chroma_port)
        except Exception:
            logger.warning(
                "ChromaDB server not available, using PersistentClient at %s",
                CHROMA_PERSIST_DIR,
            )
            self.chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)

        self.collection = self.chroma_client.get_or_create_collection(
            name=settings.chroma_collection,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            "RAG Engine initialized. Collection '%s' has %d documents.",
            settings.chroma_collection,
            self.collection.count(),
        )

    async def _get_embedding(self, text: str) -> list[float]:
        from app.services.llm_provider import llm_provider
        return await llm_provider.get_embedding(text)

    async def search(self, query: str, top_k: int = 5) -> list[dict]:
        if not self.collection or self.collection.count() == 0:
            return []

        try:
            query_embedding = await self._get_embedding(query)
        except Exception as e:
            logger.error("Embedding generation failed: %s. RAG search skipped.", str(e)[:120])
            return []

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, self.collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        formatted = []
        if results and results["ids"]:
            for i, doc_id in enumerate(results["ids"][0]):
                distance = results["distances"][0][i] if results["distances"] else 1.0
                score = 1.0 - distance

                if score < settings.rag_score_threshold:
                    continue

                formatted.append({
                    "id": doc_id,
                    "text": results["documents"][0][i] if results["documents"] else "",
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "score": round(score, 4),
                })

        return formatted

    async def get_collection_stats(self) -> dict:
        if not self.collection:
            return {"status": "not_initialized"}
        return {
            "collection": settings.chroma_collection,
            "document_count": self.collection.count(),
        }

    async def delete_chunk(self, chunk_id: str):
        if self.collection:
            self.collection.delete(ids=[chunk_id])


rag_engine = RAGEngine()
