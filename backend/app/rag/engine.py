import logging
import os
from pathlib import Path

import chromadb

from app.core.config import settings
from app.services.cache_service import TTLCache, normalize_query

logger = logging.getLogger(__name__)

CHROMA_PERSIST_DIR = os.getenv(
    "CHROMA_DATA_DIR",
    str(Path(__file__).resolve().parents[3] / "chroma_data"),
)


class RAGEngine:
    def __init__(self):
        self.chroma_client: chromadb.ClientAPI | None = None
        self.collection = None
        self._cache = TTLCache(max_items=settings.rag_cache_max_items)

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

    @staticmethod
    def _pack_query_results(results: dict, min_score: float) -> list[dict]:
        formatted: list[dict] = []
        if not results or not results.get("ids") or not results["ids"][0]:
            return formatted
        for i, doc_id in enumerate(results["ids"][0]):
            distance = results["distances"][0][i] if results.get("distances") else 1.0
            score = 1.0 - distance
            if score < min_score:
                continue
            formatted.append({
                "id": doc_id,
                "text": results["documents"][0][i] if results.get("documents") else "",
                "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                "score": round(score, 4),
            })
        return formatted

    @staticmethod
    def _merge_by_id(primary: list[dict], extra: list[dict], limit: int) -> list[dict]:
        by_id: dict[str, dict] = {}
        for row in primary + extra:
            prev = by_id.get(row["id"])
            if prev is None or row["score"] > prev["score"]:
                by_id[row["id"]] = row
        merged = sorted(by_id.values(), key=lambda x: x["score"], reverse=True)
        return merged[:limit]

    @staticmethod
    def _pipe_document_filter(query: str) -> dict | None:
        """Для вопросов про трубы/отопление — OR по подстрокам из Азбуки (полипропилен, PEX…)."""
        ql = query.lower()
        clauses: list[dict] = []
        if any(x in ql for x in ("полипропилен", "ppr", "пропилен")):
            clauses.extend([{"$contains": "полипропилен"}, {"$contains": "PPR"}])
        if any(x in ql for x in ("полиэтилен", "pex", "сшит", "сшитый")):
            clauses.extend([{"$contains": "PEX"}, {"$contains": "сшитый полиэтилен"}])
        if "металлополимер" in ql or ("алюмин" in ql and "труб" in ql):
            clauses.append({"$contains": "PEX-AL-PEX"})
        if "труб" in ql or "трубопровод" in ql or "отоплен" in ql:
            clauses.append({"$contains": "трубопровод"})
        if len(clauses) < 2:
            return None
        # уникальные dict по строке (Chroma принимает $or список)
        seen: set[str] = set()
        uniq: list[dict] = []
        for c in clauses:
            key = str(c)
            if key not in seen:
                seen.add(key)
                uniq.append(c)
        if len(uniq) < 2:
            return None
        return {"$or": uniq[:8]}

    async def search(self, query: str, top_k: int = 5) -> list[dict]:
        if not self.collection or self.collection.count() == 0:
            return []
        cache_key = f"{normalize_query(query)}|k={top_k}"
        if settings.rag_cache_enabled:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        try:
            query_embedding = await self._get_embedding(query)
        except Exception as e:
            logger.error("Embedding generation failed: %s. RAG search skipped.", str(e)[:120])
            return []

        k = top_k
        n_fetch = min(max(k, 15), self.collection.count())

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_fetch,
            include=["documents", "metadatas", "distances"],
        )

        formatted = self._pack_query_results(results, settings.rag_score_threshold)

        wd = self._pipe_document_filter(query)
        if wd and len(formatted) < 3:
            try:
                wd_results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=min(10, self.collection.count()),
                    where_document=wd,
                    include=["documents", "metadatas", "distances"],
                )
                extra = self._pack_query_results(wd_results, settings.rag_fallback_min_score)
                formatted = self._merge_by_id(formatted, extra, n_fetch)
            except Exception as e:
                logger.debug("RAG where_document supplement skipped: %s", e)

        if not formatted:
            formatted = self._pack_query_results(results, settings.rag_fallback_min_score)

        if not formatted:
            formatted = self._pack_query_results(results, 0.0)[: min(3, n_fetch)]
            if formatted:
                logger.info("RAG: used top-%d chunks without score floor (weak match)", len(formatted))

        final = formatted[:k]
        if settings.rag_cache_enabled:
            self._cache.set(cache_key, final, settings.rag_cache_ttl_seconds)
        return final

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
