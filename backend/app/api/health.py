from fastapi import APIRouter

from app.core.config import settings
from app.services.llm_provider import llm_provider

router = APIRouter()


@router.get("/health")
async def health_check():
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
    }
