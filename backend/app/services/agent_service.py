import logging
import time
from collections.abc import AsyncGenerator

from app.core.config import settings
from app.models.chat import ChatResponse, Source
from app.prompts.system import build_system_prompt
from app.rag.engine import rag_engine
from app.services.cache_service import TTLCache, normalize_query
from app.services.conversation_logger import conversation_logger
from app.services.intent_service import classify_intent
from app.services.llm_provider import llm_provider
from app.services.session_service import session_service

logger = logging.getLogger(__name__)
_response_cache = TTLCache(max_items=settings.response_cache_max_items)


class AgentService:
    """
    Backend Agent — подчинён Тимлиду.
    Обрабатывает сообщения: классифицирует intent → ищет в RAG → генерирует ответ.
    Поддерживает OpenAI и GigaChat через llm_provider.
    """

    async def process_message(
        self,
        message: str,
        session_id: str,
        metadata: dict | None = None,
    ) -> ChatResponse:
        start = time.time()
        intent = classify_intent(message)
        logger.info("Session %s | Intent: %s | Message: %s", session_id, intent, message[:80])

        history = session_service.get_history(session_id)
        cache_key = f"{normalize_query(message)}|intent={intent}"
        if settings.response_cache_enabled and not history:
            cached = _response_cache.get(cache_key)
            if cached is not None:
                duration_ms = round((time.time() - start) * 1000)
                session_service.add_message(session_id, "user", message)
                session_service.add_message(session_id, "assistant", cached["message"])
                conversation_logger.log_conversation(
                    session_id=session_id,
                    user_message=message,
                    assistant_message=cached["message"],
                    intent=intent,
                    sources=[
                        {"title": s.title, "url": s.url, "score": s.score}
                        for s in cached["sources"]
                    ],
                    tokens_used=0,
                    duration_ms=duration_ms,
                )
                return ChatResponse(
                    session_id=session_id,
                    message=cached["message"],
                    sources=cached["sources"],
                    intent=intent,
                    tokens_used=0,
                )

        rag_results = await rag_engine.search(message, top_k=settings.rag_top_k)

        rag_context = self._format_rag_context(rag_results)
        system_prompt = build_system_prompt(
            company_name=settings.company_name,
            rag_context=rag_context,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            *history,
            {"role": "user", "content": message},
        ]

        llm_response = await llm_provider.chat(messages)
        duration_ms = round((time.time() - start) * 1000)

        session_service.add_message(session_id, "user", message)
        session_service.add_message(session_id, "assistant", llm_response.content)

        sources = [
            Source(
                title=r.get("metadata", {}).get("title", ""),
                chunk_id=r.get("id", ""),
                score=r.get("score", 0.0),
                url=r.get("metadata", {}).get("url", ""),
            )
            for r in rag_results
        ]

        conversation_logger.log_conversation(
            session_id=session_id,
            user_message=message,
            assistant_message=llm_response.content,
            intent=intent,
            sources=[{"title": s.title, "url": s.url, "score": s.score} for s in sources],
            tokens_used=llm_response.tokens_used,
            duration_ms=duration_ms,
        )

        response = ChatResponse(
            session_id=session_id,
            message=llm_response.content,
            sources=sources,
            intent=intent,
            tokens_used=llm_response.tokens_used,
        )
        if settings.response_cache_enabled and not history:
            _response_cache.set(
                cache_key,
                {"message": response.message, "sources": response.sources},
                settings.response_cache_ttl_seconds,
            )
        return response

    async def process_message_stream(
        self,
        message: str,
        session_id: str,
        metadata: dict | None = None,
    ) -> AsyncGenerator[dict, None]:
        start = time.time()
        intent = classify_intent(message)
        logger.info("Session %s | Intent: %s | Stream | Message: %s", session_id, intent, message[:80])

        history = session_service.get_history(session_id)
        rag_results = await rag_engine.search(message, top_k=settings.rag_top_k)

        rag_context = self._format_rag_context(rag_results)
        system_prompt = build_system_prompt(
            company_name=settings.company_name,
            rag_context=rag_context,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            *history,
            {"role": "user", "content": message},
        ]

        full_response = ""
        async for chunk_text in llm_provider.chat_stream(messages):
            full_response += chunk_text
            yield {
                "type": "chunk",
                "content": chunk_text,
                "session_id": session_id,
            }

        duration_ms = round((time.time() - start) * 1000)

        session_service.add_message(session_id, "user", message)
        session_service.add_message(session_id, "assistant", full_response)

        sources = [
            {
                "title": r.get("metadata", {}).get("title", ""),
                "chunk_id": r.get("id", ""),
                "score": r.get("score", 0.0),
                "url": r.get("metadata", {}).get("url", ""),
            }
            for r in rag_results
        ]

        conversation_logger.log_conversation(
            session_id=session_id,
            user_message=message,
            assistant_message=full_response,
            intent=intent,
            sources=[{"title": s["title"], "url": s.get("url", ""), "score": s["score"]} for s in sources],
            tokens_used=0,
            duration_ms=duration_ms,
        )

        yield {
            "type": "complete",
            "intent": intent,
            "sources": sources,
            "session_id": session_id,
        }

    def _format_rag_context(self, results: list[dict]) -> str:
        if not results:
            return "Контекст не найден в базе знаний."
        parts = []
        for i, r in enumerate(results, 1):
            title = r.get("metadata", {}).get("title", "Без названия")
            category = r.get("metadata", {}).get("category", "")
            url = r.get("metadata", {}).get("url", "")
            text = r.get("text", "")
            score = r.get("score", 0)
            source_type = r.get("metadata", {}).get("source_type", "")
            if url and url != "https://gkproject.ru":
                url_line = f"\nСсылка: {url}"
            elif source_type == "internal_document" or not url:
                url_line = "\nСсылка: НЕТ (внутренний документ компании, не давай ссылку в ответе)"
            else:
                url_line = ""
            parts.append(
                f"[{i}] {title} (категория: {category}, релевантность: {score}):{url_line}\n{text}"
            )
        return "\n\n".join(parts)


agent_service = AgentService()
