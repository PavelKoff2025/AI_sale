from fastapi import APIRouter

from app.core.config import settings
from app.services.llm_provider import llm_provider, MAX_CONCURRENT_LLM, get_llm_in_use
from app.services.session_service import session_service
from app.services.voice_service import voice_service

router = APIRouter()


@router.get("/health")
async def health_check():
    from app.api.chat import get_active_connections_count, MAX_WS_CONNECTIONS

    provider_name = settings.llm_provider
    if hasattr(llm_provider, "active_provider_name"):
        provider_name = f"auto ({llm_provider.active_provider_name})"
    elif hasattr(llm_provider, "name"):
        provider_name = llm_provider.name

    return {
        "status": "healthy",
        "service": "ai-sale-backend",
        "version": "0.1.0",
        "llm_provider": provider_name,
        "active_sessions": session_service.active_sessions_count(),
        "websocket_connections": get_active_connections_count(),
        "websocket_limit": MAX_WS_CONNECTIONS,
        "llm_concurrent": get_llm_in_use(),
        "llm_concurrent_limit": MAX_CONCURRENT_LLM,
        "voice_enabled": voice_service.enabled,
    }
